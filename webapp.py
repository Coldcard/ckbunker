#!/usr/bin/env python
#
# A web server.
#
import sys, os, asyncio, logging, aiohttp_jinja2, jinja2, time, weakref, re
from aiohttp import web
from yarl import URL
from conn import Connection, MissingColdcard
from ckcc.protocol import CCProtocolPacker
from utils import pformat_json, json_loads, json_dumps, cleanup_psbt
from objstruct import ObjectStruct
from aiohttp.web_exceptions import HTTPMovedPermanently, HTTPNotFound, HTTPBadRequest, HTTPFound
from decimal import Decimal
import aiohttp_session
from aiohttp_session import get_session, new_session
from base64 import b32encode, b64decode, b64encode
from binascii import b2a_hex, a2b_hex
from status import STATUS
from persist import settings, BP
from hashlib import sha256
from chain import broadcast_txn
from version import VERSION
from jinja2 import Markup
import policy

from ckcc.constants import USER_AUTH_TOTP, USER_AUTH_HMAC, USER_AUTH_SHOW_QR, MAX_USERNAME_LEN
from ckcc.constants import STXN_VISUALIZE, STXN_SIGNED, AF_P2WPKH, AF_CLASSIC
from ckcc.protocol import CCUserRefused

logging.getLogger(__name__).addHandler(logging.NullHandler())

routes = web.RouteTableDef()

web_sockets = weakref.WeakSet()

class HTMLErrorMsg(ValueError):
    def __init__(self, html):
        super(HTMLErrorMsg, self).__init__(Markup(html))

APPROVE_CTA = '''\
Please consult the Coldcard screen and review the HSM policy shown there. If you \
are satisfied it does what you need, approve the policy and the Coldcard will enter HSM mode.
'''

def default_context():
    #
    # Put values you want in every template here. They cannot vary per-request.
    #
    rv = ObjectStruct(VERSION=VERSION)

    # this defines the nav menu in top bar
    rv.PAGES = [    ('/', 'Sign Transaction'),
                    ('/tools', 'Tools'),
                    ('/setup', 'Coldcard Setup'),
                    ('/bunker', 'Bunker Setup'),
                    #('/help', 'Help') 
                ]

    rv['zip'] = zip

    return rv

async def add_shared_ctx(request, **rv):
    # add ctx vars needed to support fancy Vue.js stuff on logged-in pages

    ses = await get_session(request)


    rv.update(dict(
        ws_url = '/websocket/' + ses.get('ws_token'),
        STATUS=STATUS.as_dict(),
    ))

    rv['CUR_PAGE'] = '/' + request.path.split('/')[-1]

    return rv

@routes.get('/')
@aiohttp_jinja2.template('txn/index.html')
async def homepage(request):

    # may take some details from the policy, and cook up into more useful forms

    ss = BP.get('summary', None) if STATUS.hsm.get('active') else None

    # coldcard tells us when we'll need a local code, by providing seed value
    nl = bool('next_local_code' in STATUS.hsm)

    return await add_shared_ctx(request, policy_summary=ss, needs_local=nl)

@routes.get('/setup')
@aiohttp_jinja2.template('setup/index.html')
async def setup_page(request):
    # HSM policy setup

    # get latest status
    dev = Connection()
    await dev.hsm_status()

    return await add_shared_ctx(request)

@routes.get('/bunker')
@aiohttp_jinja2.template('bunker/index.html')
async def bunker_page(request):

    # Bunker config and setup

    # get latest status
    dev = Connection()
    await dev.hsm_status()

    from torsion import TOR

    return await add_shared_ctx(request, BP=BP, force_local_mode=STATUS.force_local_mode)


@routes.get('/tools')
@aiohttp_jinja2.template('tools/index.html')
async def tools_page(request):
    # various random things I've been talked into
    # - message signing useul tho
    if BP.get('policy'):
        paths = BP['policy'].get('msg_paths') or []
        paths = set(i.replace('*', '999') for i in paths if i != 'any')
    else:
        # priv_over_ux: we don't know, but some useful ones
        paths = ['m', "m/0/0", "m/44'/0'/0'/0/0", "m/49'/0'/0'/0/0", 
                    "m/84'/0'/0/0" ]

    paths = list(sorted(paths, key=lambda x: (len(x.split('/')), x.split('/'))))

    return await add_shared_ctx(request, msg_paths=paths)

@routes.get('/help')
@aiohttp_jinja2.template('help.html')
async def help_page(request):
    return await add_shared_ctx(request)


_static_html_cache = dict()
def send_static_html(fname, disable_cache=True):
    # just return the contents of an HTML file, and cache it along the way
    # - can't use web.StaticFileResponse because want set-cookies to happen
    global _static_html_cache

    if not disable_cache and (fname in _static_html_cache):
        page_html = _static_html_cache[fname]
    else:
        _static_html_cache[fname] = page_html = open(fname, 'rt').read()

    return web.Response(text=page_html, content_type='text/html')

@routes.get('/logout')
async def logout_page(request):
    # do a logout
    ses = await get_session(request)
    if ses and not ses.new:
        logging.warn("Logout of user.")

    # This clears cookie, but if they come back to any page on our site,
    # they will get a new one, so we can't redirect them to any other page
    # here
    ses.invalidate()

    return send_static_html('static/html/logout.html')

@routes.get('/login')
async def login_page(request):
    # Completely static and plain.
    # thanks to <https://codepen.io/rizwanahmed19/pen/KMMoEN>

    # Create a session, if they don't have one. Need this
    # to establish timing/authencity of login data when its posted
    ses = await get_session(request)
    if not ses:
        ses = await new_session(request)
    else:
        if ses.get('login_ok'):
            # they are already logged in, so send them to homepage
            return HTTPFound('/')

    # - cannot leave session empty, so put anything in there.
    ses['j'] = True
    ses.changed()

    return send_static_html('static/html/login.html')


def accept_user_login(ses):
    # setup session for good user
    ses['login_ok'] = True
    ses['active'] = time.time()
    ses['ws_token'] = str(b32encode(os.urandom(15)), 'ascii')
    ses.pop('captcha', None)

@routes.post('/login')
async def login_post(request):

    # they must have a current session already
    # - hope this is enough against CSRF
    # - TODO: some rate limiting here, without DoS attacks
    ses = await get_session(request)
    form = await request.post()
    ok = False

    if ses.new:
        logging.warn("Bad login attempt (no cookie)")

    elif (time.time() - ses.created) > settings.MAX_LOGIN_WAIT_TIME:
        ses.invalidate()
        logging.warn("Stale login attempt (cookie too old)")

    elif ses.get('kiddie', 0):
        logging.warn("Keeping the kiddies at bay")

    else:
        captcha = form.get('captcha', '').lower()
        pw = form.get('password', None)

        if not captcha or not pw:
            # keep same captcha; they just pressed enter
            ok = False

        else:
            expect = BP.get('master_pw', settings.MASTER_PW)        # XXX scrypt(pw)
            expect_code = ses.pop('captcha', None)

            ok = (pw == expect) and (captcha == expect_code)

    if not ok:
        # fail; do nothing visible (but they will get new captcha)
        dest = URL(request.headers.get('referer', '/login'))
        return HTTPFound(dest)

    # SUCCESS
    accept_user_login(ses)

    # try to put them back where they were before
    try:
        dest = URL(request.headers.get('referer', '')).query.get('u', '/')
    except:
        dest = '/'

    logging.warn(f"Good login from user, sending to: {dest}")

    return HTTPFound(dest)

@routes.get('/captcha')
async def captcha_image(request):
    # make a captcha image, but always the same one per session

    ses = await get_session(request)
    if ses.new:
        return HTTPNotFound()

    from make_captcha import RansomCaptcha, MegaGifCaptcha, TOKEN_CHARS
    import random

    if 'captcha' in ses:
        # dont let them retry?
        code = ses['captcha']
    else:
        code = ''.join(random.sample(TOKEN_CHARS, 8))
        ses['captcha'] = code

    easy = BP.get('easy_captcha', settings.EASY_CAPTCHA)
    if easy:
        itype, data = RansomCaptcha(seed=code).draw(code, foreground='#444')
    else:
        itype, data = MegaGifCaptcha(seed=code).draw(code, foreground='#444')

    return web.Response(body=data, content_type='image/'+itype, 
        headers = {'Cache-Control': 'no-cache'})
    

async def rx_handler(ses, ws, orig_request):
    # Block on receive, handle each message as it comes in.
    # see pp/aiohttp/client_ws.py

    async def tx_resp(_ws=ws, **resp):
        logging.debug(f"Send resp: {resp}")
        await _ws.send_str(json_dumps(resp))


    async for msg in ws:
        if msg.type != web.WSMsgType.TEXT:
            raise TypeError('expected text')

        try:
            assert len(msg.data) < 20000
            req = json_loads(msg.data)

            if '_ping' in req:
                # connection keep alive, simple
                await tx_resp(_pong=1)
                continue

            # Caution: lots of sensitive values here XXX
            #logging.info("WS api data: %r" % req)

        except Exception as e:
            logging.critical("Junk data on WS", exc_info=1)
            break # the connection

        # do something with the request
        failed = True
        try:
            await ws_api_handler(ses, tx_resp, req, orig_request)
            failed = False
        except SystemExit:
            raise
        except KeyboardInterrupt:
            break
        except HTMLErrorMsg as exc:
            # pre-formated text for display
            msg = exc.args[0]
        except RuntimeError as exc:
            # covers CCProtoError and similar
            msg = str(exc) or str(type(exc).__name__)
        except BaseException as exc:
            logging.exception("API fail: req=%r" % req)
            msg = str(exc) or str(type(exc).__name__)

        if failed:
            # standard error response
            await tx_resp(show_modal=True, html=jinja2.escape(msg), selector='.js-api-fail')

async def push_status_updates_handler(ws):
    # block for a bit, and then send display updates (and all other system status changes)

    # - there is no need for immediate update because when we rendered the HTML on page
    #   load, we put in current values.
    await asyncio.sleep(0.250)

    last = None
    while 1:
        # get latest state
        now = STATUS.as_dict()

        if last != now:
            # it has changed, so send it.
            await ws.send_str(json_dumps(dict(vue_app_cb=dict(update_status=now))))
            last = now

        # wait until next update, or X seconds max (for keep alive/just in case)
        try:
            await asyncio.wait_for(STATUS._update_event.wait(), 120)
        except asyncio.TimeoutError:
            # force an update
            last = None

async def ws_api_handler(ses, send_json, req, orig_request):     # handle_api
    #
    # Handle incoming requests over websocket; send back results.
    # req = already json parsed request coming in
    # send_json() = means to send the response back
    #
    action = req.action
    args = getattr(req, 'args', None)

    #logging.warn("API action=%s (%r)" % (action, args))        # MAJOR info leak XXX
    logging.debug(f"API action={action}")

    if action == '_connected':
        logging.info("Websocket connected: %r" % args)

        # can send special state update at this point, depending on the page

    elif action == 'start_hsm_btn':
        await Connection().hsm_start()
        await send_json(show_flash_msg=APPROVE_CTA)
        
    elif action == 'delete_user':
        name, = args
        assert 1 <= len(name) <= MAX_USERNAME_LEN, "bad username length"
        await Connection().delete_user(name.encode('utf8'))

        # assume it worked, so UX updates right away
        try:
            STATUS.hsm.users.remove(name)
        except ValueError:
            pass
        STATUS.notify_watchers()

    elif action == 'create_user':
        name, authmode, new_pw = args

        assert 1 <= len(name) <= MAX_USERNAME_LEN, "bad username length"
        assert ',' not in name, "no commas in names"

        if authmode == 'totp':
            mode = USER_AUTH_TOTP | USER_AUTH_SHOW_QR
            new_pw = ''
        elif authmode == 'rand_pw':
            mode = USER_AUTH_HMAC | USER_AUTH_SHOW_QR
            new_pw = ''
        elif authmode == 'give_pw':
            mode = USER_AUTH_HMAC
        else:
            raise ValueError(authmode)

        await Connection().create_user(name.encode('utf8'), mode, new_pw)

        # assume it worked, so UX updates right away
        try:
            STATUS.hsm.users = list(set(STATUS.hsm.users + [name]))
        except ValueError:
            pass
        STATUS.notify_watchers()

    elif action == 'submit_policy':
        # get some JSON w/ everything the user entered.
        p, save_copy = args

        proposed = policy.web_cleanup(json_loads(p))

        policy.update_sl(proposed)

        await Connection().hsm_start(proposed)

        STATUS.notify_watchers()

        await send_json(show_flash_msg=APPROVE_CTA)

        if save_copy:
            d = policy.desensitize(proposed)
            await send_json(local_download=dict(data=json_dumps(d, indent=2),
                                filename=f'hsm-policy-{STATUS.xfp}.json.txt'))

    elif action == 'download_policy':

        proposed = policy.web_cleanup(json_loads(args[0]))
        await send_json(local_download=dict(data=json_dumps(proposed, indent=2),
                                filename=f'hsm-policy-{STATUS.xfp}.json.txt'))

    elif action == 'import_policy':
        # they are uploading a JSON capture, but need values we can load in Vue
        proposed = args[0]
        cooked = policy.web_cookup(proposed)
        await send_json(vue_app_cb=dict(update_policy=cooked),
                        show_flash_msg="Policy file imported.")

    elif action == 'pick_onion_addr':
        from torsion import TOR
        addr, pk = await TOR.pick_onion_addr()
        await send_json(vue_app_cb=dict(new_onion_addr=[addr, pk]))

    elif action == 'pick_master_pw':
        pw = b64encode(os.urandom(12)).decode('ascii')
        pw = pw.replace('/', 'S').replace('+', 'p')
        assert '=' not in pw

        await send_json(vue_app_cb=dict(new_master_pw=pw))

    elif action == 'new_bunker_config':
        from torsion import TOR
        # save and apply config values
        nv = json_loads(args[0])

        assert 4 <= len(nv.master_pw) < 200, "Master password must be at least 4 chars long"

        # copy in simple stuff
        for fn in [ 'tor_enabled', 'master_pw', 'easy_captcha', 'allow_reboots']:
            if fn in nv:
                BP[fn] = nv[fn]


        # update onion stuff only if PK is known (ie. they changed it)
        if nv.get('onion_pk', False) or False:
            for fn in [ 'onion_addr', 'onion_pk']:
                if fn in nv:
                    BP[fn] = nv[fn]

        BP.save()

        await send_json(show_flash_msg="Bunker settings encrypted and saved to disk.")

        STATUS.tor_enabled = BP['tor_enabled']
        STATUS.notify_watchers()

        if not BP['tor_enabled']:
            await TOR.stop_tunnel()
        elif BP.get('onion_pk') and not (STATUS.force_local_mode or STATUS.setup_mode):
            # connect/reconnect
            await TOR.start_tunnel()

    elif action == 'sign_message':
        # sign a short text message
        # - lots more checking could be done here, but CC does it anyway
        msg_text, path, addr_fmt = args

        addr_fmt = AF_P2WPKH if addr_fmt != 'classic' else AF_CLASSIC

        try:
            sig, addr = await Connection().sign_text_msg(msg_text, path, addr_fmt)
        except:
            # get the spinner to stop: error msg will be "refused by policy" typically
            await send_json(vue_app_cb=dict(msg_signing_result='(failed)'))
            raise

        sig = b64encode(sig).decode('ascii').replace('\n', '')

        await send_json(vue_app_cb=dict(msg_signing_result=f'{sig}\n{addr}'))

    elif action == 'upload_psbt':
        # receiving a PSBT for signing

        size, digest, contents = args
        psbt = b64decode(contents)
        assert len(psbt) == size, "truncated/padded in transit"
        assert sha256(psbt).hexdigest() == digest, "corrupted in transit"

        STATUS.import_psbt(psbt)
        STATUS.notify_watchers()

    elif action == 'clear_psbt':
        STATUS.clear_psbt()
        STATUS.notify_watchers()

    elif action == 'preview_psbt':
        STATUS.psbt_preview = 'Wait...'
        STATUS.notify_watchers()
        try:
            txt = await Connection().sign_psbt(STATUS._pending_psbt, flags=STXN_VISUALIZE)
            txt = txt.decode('ascii')
            # force some line splits, especially for bech32, 32-byte values (p2wsh)
            probs = re.findall(r'([a-zA-Z0-9]{36,})', txt)
            for p in probs:
                txt = txt.replace(p, p[0:30] + '\u22ef\n\u22ef' + p[30:])
            STATUS.psbt_preview = txt
        except:
            # like if CC doesn't like the keys, whatever ..
            STATUS.psbt_preview = None
            raise
        finally:
            STATUS.notify_watchers()

    elif action == 'auth_set_name':
        idx, name = args

        assert 0 <= len(name) <= MAX_USERNAME_LEN
        assert 0 <= idx < len(STATUS.pending_auth)

        STATUS.pending_auth[idx].name = name
        STATUS.notify_watchers()

    elif action == 'auth_offer_guess':
        idx, ts, guess = args
        assert 0 <= idx < len(STATUS.pending_auth)
        STATUS.pending_auth[idx].totp = ts
        STATUS.pending_auth[idx].has_guess = 'x'*len(guess)
        STATUS._auth_guess[idx] = guess
        STATUS.notify_watchers()

    elif action == 'submit_psbt':
        # they want to sign it now
        expect_hash, send_immediately, finalize, wants_dl = args

        assert expect_hash == STATUS.psbt_hash, "hash mismatch"
        if send_immediately: assert finalize, "must finalize b4 send"

        logging.info("Starting to sign...")
        STATUS.busy_signing = True
        STATUS.notify_watchers()

        try:
            dev = Connection()

            # do auth steps first (no feedback given)
            for pa, guess in zip(STATUS.pending_auth, STATUS._auth_guess):
                if pa.name and guess:
                    await dev.user_auth(pa.name, guess, int(pa.totp), a2b_hex(STATUS.psbt_hash))

            STATUS.reset_pending_auth()

            try:
                result = await dev.sign_psbt(STATUS._pending_psbt, finalize=finalize)
                logging.info("Done signing")

                msg = "Transaction signed."

                if send_immediately:
                    msg += '<br><br>' + broadcast_txn(result)

                await send_json(show_modal=True, html=Markup(msg), selector='.js-api-success')

                result = (b2a_hex(result) if finalize else b64encode(result)).decode('ascii')
                fname = 'transaction.txt' if finalize else ('signed-%s.psbt'%STATUS.psbt_hash[-6:])

                if wants_dl:
                    await send_json(local_download=dict(data=result, filename=fname,
                                                        is_b64=(not finalize)))

                await dev.hsm_status()
            except CCUserRefused:
                logging.error("Coldcard refused to sign txn")
                await dev.hsm_status()
                r = STATUS.hsm.get('last_refusal', None)
                if not r: 
                    raise HTMLErroMsg('Refused by local user.')
                else:
                    raise HTMLErrorMsg(f"Rejected by Coldcard.<br><br>{r}")

        finally:
            STATUS.busy_signing = False
            STATUS.notify_watchers()

    elif action == 'shutdown_bunker':
        await send_json(show_flash_msg="Bunker is shutdown.")
        await asyncio.sleep(0.25)
        logging.warn("User-initiated shutdown")
        asyncio.get_running_loop().stop()
        sys.exit(0)

    elif action == 'leave_setup_mode':
        # During setup process, they want to go Tor mode; which I consider leaving
        # setup mode ... in particular, logins are required.
        # - button label is "Start Tor" tho ... so user doesn't see it that way
        assert STATUS.setup_mode, 'not in setup mode?'
        assert BP['tor_enabled'], 'Tor not enabled (need to save?)'
        addr = BP['onion_addr']
        assert addr and '.onion' in addr, "Bad address?"

        STATUS.setup_mode = False
        await send_json(show_flash_msg="Tor hidden service has been enabled. "
                            "It may take a few minutes for the website to become available")
        STATUS.notify_watchers()

        from torsion import TOR
        logging.info(f"Starting hidden service: %s" % addr)
        asyncio.create_task(TOR.start_tunnel())

    elif action == 'logout_everyone':
        # useful for running battles...
        # - changes crypto key for cookies, so they are all invalid immediately.
        from aiohttp_session.nacl_storage import NaClCookieStorage
        import nacl

        logging.warning("Logout of everyone!")

        # reset all session cookies
        storage = orig_request.get('aiohttp_session_storage')
        assert isinstance(storage, NaClCookieStorage)
        storage._secretbox = nacl.secret.SecretBox(os.urandom(32))

        # kick everyone off (bonus step)
        for w in web_sockets:
            try:
                await send_json(redirect='/logout', _ws=w)
                await w.close()
            except:
                pass

    else:
        raise NotImplementedError(action)


@routes.get('/websocket/{token}')
async def api_websocket(request):
    '''
        Stream display activity as HTML fragments
        - accept config changes
        - and more?
    '''

    try:
        ses = await get_session(request)
        assert not ses.new
        assert ses['login_ok']
        token = request.match_info['token']
        assert token == ses['ws_token'], ses.get('ws_token')
    except:
        logging.exception("Bad websocket link")
        raise web.HTTPForbidden

    # begin a streaming response
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    web_sockets.add(ws)

    try:
        api_rx = asyncio.create_task(rx_handler(ses, ws, request))
        dis_tx = asyncio.create_task(push_status_updates_handler(ws))

        await asyncio.gather(api_rx, dis_tx)
    finally:
        api_rx.cancel()
        dis_tx.cancel()
        await ws.close()

    return ws


@routes.get('/{fname}.php')
@routes.get('/{path}/{fname}.php')
@routes.get('/admin')
async def kiddie_traps(request):
    # I hate skill-less people running burpsuite! Track them
    ses = await get_session(request)

    ses['kiddie'] = ses.get('kiddie', 0) + 1

    return HTTPFound("/login")

@routes.get('/favicon.ico')
@routes.get('/robots.txt')
@routes.get('/humans.txt')
async def expected_404s(request):
    # we are expecting these URL's to 404
    # - don't redirect to login
    return HTTPNotFound()


@routes.get('/static/ext/themes/default/assets/fonts/{fname}')
async def remap_fonts(request):
    fn = request.match_info['fname']
    # remap some links so we don't need to edit Semantic files.
    return HTTPMovedPermanently('/static/ext/semantic-fonts/' + fn)

def extra_filters(app):

    def my_time(dt):
        if dt is None: return None
        try:
            dt = pendulum.instance(dt)
        except ValueError:
            return repr(dt)
        return dt.in_tz('local').strftime('%l:%M%p').lower()

    def my_date(dt):
        if dt is None: return None
        try:
            dt = pendulum.instance(dt)
        except ValueError:
            return repr(dt)
        return dt.in_tz('local').strftime('%b %e')

    def duration(i):
        if i < 90:
            return '%d seconds' % i
        else:
            return '%d:%02d minutes' % (i//60, i%60)

    def extlink(url, label=None):

        # in the templates, use like this: 
        #       {{ "http://sdfsfd/sdf/sdf/" | extlink( "Hello") }}    
        if not label:
            from urllib.parse import urlparse
            label = urlparse(url).netloc.lower()
            if label[0:4] == 'www.':
                label = label[4:]

        rv = f'<a href="{url}" rel="nofollow" class="extlink" '\
                'target="external" title="External site: Opens in new tab">'\
                f'{label} <i class="external alternate icon"></i></a>'

        return Markup(rv)

    def link_txn(txn_hash):
        from chain import link_to_txn
        url = link_to_txn(txn_hash)
        return extlink(url, label=txn_hash)

    def link_to_explorer(unused):
        url = settings.EXPLORA
        label = 'Bitcoin Explorer'
        if STATUS.is_testnet:
            label = 'Testnet Explorer'
            url += '/testnet'
        return extlink(url, label=label)

    def slugify(t):
        return t.lower().strip().replace('&', 'and').replace(' ', '-')

    rv = locals().copy()

    return rv

@web.middleware
async def auth_everything(request, handler):

    # during setup, no login needed
    if STATUS.force_local_mode or STATUS.setup_mode:
        # bypass security completely
        ses = await get_session(request)
        if not ses:
            ses = await new_session(request)
            accept_user_login(ses)
        return await handler(request)

    # whitelist of pages that do not need login
    # all other requests will need auth
    if handler in { login_page, login_post, captcha_image, kiddie_traps, expected_404s }:
        return await handler(request)

    # verify auth
    ses = await get_session(request)
    if ses:
        active = ses.get('active', 0)
        idle = time.time() - active
        if idle > settings.MAX_IDLE_TIME:
            # stale / idle timeout
            logging.warn("Idle timeout")
            ses.invalidate()
            ses = None
            
    if not ses:
        # no cookie/stale cookie, so send them to logout/in page
        u = URL("/login")
        target = request.path[1:]
        if target and target != 'logout':
            u = u.update_query(u=target)

        return HTTPFound(u)

    # normal path: continue to page

    ses['active'] = time.time()

    resp = await handler(request)

    # clearly an HTML request, so force no caching
    if '/static/' not in request.path:
        resp.headers['Cache-Control'] = 'no-cache'

    return resp

def startup(setup_mode):
    # Entry point. Return an awaitable to be run.

    # encrypted cookies for session logic
    from aiohttp_session.nacl_storage import NaClCookieStorage
    from aiohttp_session import session_middleware
    todays_key = os.urandom(32)
    sml =  session_middleware(NaClCookieStorage(todays_key, cookie_name='X'))

    # create app: order of middlewares matters
    app = web.Application(middlewares=[sml, auth_everything])
    app.add_routes(routes)
    app.router.add_static('/static', './static')

    # hack to obfuscate our identity a little
    # - from <https://w3techs.com/technologies/details/ws-nginx/1>  23% market share
    import aiohttp.web_response as ht
    ht.SERVER_SOFTWARE = 'nginx/1.14.1'

    j_env = aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'),
                                        filters=extra_filters(app))
    j_env.globals.update(default_context())
    j_env.policies['json.dumps_function'] = json_dumps

    my_url = f"http://localhost:{settings.PORT_NUMBER}" + ('/setup' if setup_mode else '')
    logging.info(f"Web server at:    {my_url}")

    # meh; kinda annoying.
    if 0:
        def popup():
            try:
                # see <https://github.com/jupyter/notebook/issues/3746#issuecomment-444957821>
                # if this doesn't happen on MacOS
                from webbrowser import open as open_browser
                open_browser(my_url)
            except:
                logging.error("Unable to pop browser open", exc_info=1)
        asyncio.get_running_loop().call_later(3, popup)

    from aiohttp.abc import AbstractAccessLogger
    class AccessLogger(AbstractAccessLogger):
        def log(self, request, response, time):
            self.logger.info(f'{response.status} <= {request.method} {request.path}')

    return web._run_app(app, port=settings.PORT_NUMBER, print=None, access_log_class=AccessLogger)

if __name__ == "__main__":
    from utils import setup_logging
    setup_logging()
    dev = Connection(None)      # won't do anything tho, because async dev.run not called
    asyncio.run(startup())

# EOF

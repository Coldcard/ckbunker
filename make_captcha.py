# -*- coding: utf-8 -*-
#
# Draw a Captchas ... not meant to be hard, but easier to replace out, and challenging
# to read image itself..
#
import random, os, io
from PIL import Image, ImageDraw, ImageFont

# Avoid similar-looking letters/numbers.
TOKEN_CHARS = 'abcdefghkmnpqrstuvwxyz23456789'

class CaptchaMaker:
    size = (256, 64)                # limited by iphone case. esp. when entering value

    def __init__(self, seed=None):
        self.rng = random.Random(seed)


    def draw(self, token):
        # draw some crazy captcha for indicated token and return as a 
        # tuple: extension, raw_data
        raise NotImplementedError

    def get_font(self, size=40, which='nova'):
        fn = { 'ransom': 'static/fonts/ransom-note.ttf', 
                 'nova': 'static/fonts/proximanova-semibold.ttf'
             }
        return ImageFont.truetype(fn[which], size)

class RansomCaptcha(CaptchaMaker):
    #
    # Just the simple ransom note that most people expect today.
    #
    def draw(self, token, foreground='#000', seed=None):
        fn = self.get_font(size=40, which='ransom')
        w,h = self.size
        _,_,dx,dy = fn.getbbox('W')

        im = Image.new('RGBA', self.size)
        dr = ImageDraw.Draw(im)

        # some of the lower-case letters are confusing, so replace them
        remap = dict(x = 'X', s='S', a='A', g='G', q='Q')

        x = 10
        ix = (w - (x*2)) * (len(token)-2) / dx
        for ch in token:
            ch = remap.get(ch, ch)
            y = self.rng.randint(-5, h-dy+5)
            dr.text( (x, y), ch, fill=foreground, font=fn)
            x += ix

        data = io.BytesIO()
        im.save(data, format='png')

        return 'png', data.getvalue()

class MegaGifCaptcha(CaptchaMaker):
    # These are fun, but too large to be practical? Keep in toolbox for later.

    def draw(self, token, foreground='#fff', background='white'):

        token = ' '.join(token.upper())

        fn = self.get_font(size=30, which='nova')
        w,h = self.size
        _,_,dx,dy = fn.getbbox('W')

        randint = self.rng.randint
        sample = self.rng.sample

        actual = []
        pass_thru = set()
        frames = []

        ans_y = self.rng.randint(3, h-dy-3)
        ans_w = fn.getbbox(token)[2]
        count = 15

        for fr_num in range(count):
            im = Image.new('P', self.size, background)
            dr = ImageDraw.Draw(im)

            # give them noise chars, except they are mostly correct so that
            # the order is not so clear at all. don't want to just be able to 
            # pick the most common chars observed
            charset = set(token)
            while len(charset) < len(token) + 4:
                charset.add(sample(TOKEN_CHARS, 1)[0])

            for k in range(int(w * 1.5/dx)):
                #ch = ''.join(self.rng.sample(TOKEN_CHARS, 1)).upper()
                ch = ''.join(sample(charset, 1)).upper()
                x = randint(-dx, w)
                y = ans_y + randint(int(-dy*3/4), int(dy*3/4))
                dr.text( (x,y), ch, fill=foreground, font=fn)

            frames.append(im)

            x = (w-ans_w)*fr_num / count
            dr.text( (x, ans_y), token, fill=foreground, font=fn)

        data = io.BytesIO()

        frames[0].save(data, format='gif', save_all=True, loop=0,
                            append_images=frames + list(reversed(frames[1:-1])))

        return 'gif', data.getvalue()

# EOF

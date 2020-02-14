
function ready(fn)
{
  if (document.attachEvent ? document.readyState === "complete" : document.readyState !== "loading"){
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
}

ready(function() {

    // after JQ loaded...

    $('.js-api-btn').on('click', function() {
      var el = $(this);
      var action = el.data('api-action');
      var picker = $('input[type=checkbox].js-api-picker');

      // limitation: arg cannot be falsy
      var req = { action: action,
                    noun: el.data('api-noun') || window.PAGE_NOUN || '',
                    arg: el.data('api-arg') || null };

      if(picker.length) {
        picker.each(function(index, chk) {
            if(chk.checked) {
                if(req.noun) req.noun += ',';
                req.noun += $(chk).data('api-noun');
            }
        });
      }

      console.log("ACTION: " + window.PAGE_NOUN + " => " + action);

      window.WEBSOCKET('api', req);
    });

    $('.js-api-clear-all').on('click', function() {
      $('input[type=checkbox].js-api-picker').prop('checked', false);
    });
    $('.js-api-set-all').on('click', function() {
      $('input[type=checkbox].js-api-picker').prop('checked', true);
    });

    $('body').on('click', '.js-clickable', function(evt) {
        var el = $(this)
        var target = el.data("href");
        if(!target) return;


        // special case cell, probably has input
        var cell = $(evt.target);
        if(cell.hasClass('js-not-clickable')) return;
        var td = $(evt.target).parents('td');
        if(td && td.hasClass('js-not-clickable')) return;

        var tabname = el.data("tabname");
        if(tabname) {
            window.open(target, tabname);
        } else {
            window.location = target;
        }
    });


    // Semantic UI modules that we use
    $('.ui.dropdown').dropdown({fullTextSearch: true});
    $('.ui.checkbox').checkbox();
    $('.ui.accordion').accordion();
    $('.ui.popup').popup();
    $('.js-long-popup').popup({ inline: true });

    $('.message .close').on('click', function() {
        $(this)
          .closest('.message')
          .transition('slide down')
        ;
      });


    if(window.WEBSOCKET_URL) {

        var WS = new WebSocket( (location.protocol == 'http:' ? 'ws://' : 'wss://') 
                                    + location.host + window.WEBSOCKET_URL);
        var keepalive = 0;
        
        WS.onopen = function(e) {

            console.log("websocket ready");
            keepalive = window.setInterval(function() {
                WS.send(JSON.stringify({_ping: 1}));
            }, 10000);

            
            WS.send(JSON.stringify({action: '_connected', args: [window.location.pathname]}));
        }

        WS.onmessage = function(e) {
            var r = JSON.parse(e.data);
            if(r.keepalive) return;

            if(r.show_modal) {
                // show a modal
                var el = $(r.selector);
                el.find('.content').html(r.html);
                el.modal('show');
            } else if(r.html && r.selector) {
                // XXX bad idea, delete?
                var el = $(r.selector);
                if(el) el.html(r.html);
            }
            if(r.show_flash_msg) {
                // update content in a message and show it
                var el = $('#js-flash-msg');

                el.find('.js-content').text(r.show_flash_msg);

                if(!el.transition('is visible')) {
                    el.transition('slide down');
                }
            }
            if(r.redirect) {
                location.href = r.redirect;
            }
            if(r.reload) {
                setTimeout(function() { location.reload() }, 100);
            }
            if(r.local_download) {
                // trigger download/save-as to user's system
                data = r.local_download.data
                if(r.is_b64) {
                    data = base64js.fromByteArray(data);
                }
                download(r.local_download.filename, data)
            }

            // send data back to VUE code
            if(r.vue_app_cb) {
                window.vue_app_cb(r.vue_app_cb)
            }

            if(r.cb) {
                // obsolete
                window.ws_cb(r)
            }
        };
        function done(e) {
            // show we are broken.
            console.log("websocket broken");
            window.clearInterval(keepalive);
            $('#ws_fail_msg').show();
            $('.ui.main.container input,select').attr('disabled', true);
            $('.field').addClass('disabled');
        }
        WS.onerror = done;
        WS.onclose = done;

        window.WEBSOCKET = function(action) {       // accepts varargs
            let args = Array.prototype.slice.call(arguments, 1);
            WS.send(JSON.stringify({action: action, args: args}));
        }
    }

});

function download(filename, text) {
// from <https://ourcodeworld.com/articles/read/189/how-to-create-a-file-and-generate-a-download-with-javascript-in-the-browser-without-a-server>

  var element = document.createElement('a');
  element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
  element.setAttribute('download', filename);

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);
}


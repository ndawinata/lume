var Clock = (function(){

    var exports = function(element, offset) {
        this._element = element;
        this._offset = offset || 0;
        var html = '';
        for (var i = 0; i < 6; i++) {
            html += '<span>&nbsp;</span>';
        }
        this._element.innerHTML = html;
        this._slots = this._element.getElementsByTagName('span');
        this._tick();
    };

    exports.prototype = {

        _tick:function() {
            var time = new Date();
            var utcTime = new Date(time.getTime() + (this._offset * 60 * 60 * 1000));
            this._update(this._pad(utcTime.getHours()) + this._pad(utcTime.getMinutes()) + this._pad(utcTime.getSeconds()));
            var self = this;
            setTimeout(function(){
                self._tick();
            },1000);
        },

        _pad:function(value) {
            return ('0' + value).slice(-2);
        },

        _update:function(timeString) {
            var i = 0, l = this._slots.length, value, slot, now;
            for (; i < l; i++) {
                value = timeString.charAt(i);
                slot = this._slots[i];
                now = slot.dataset.now;

                if (!now) {
                    slot.dataset.now = value;
                    slot.dataset.old = value;
                    continue;
                }

                if (now !== value) {
                    this._flip(slot,value);
                }
            }
			
        },

        _flip:function(slot,value) {
            // setup new state
            slot.classList.remove('flip');
            slot.dataset.old = slot.dataset.now;
            slot.dataset.now = value;

            // force dom reflow
            slot.offsetLeft;

            // start flippin
            slot.classList.add('flip');
        }

    };

    return exports;
}());


var clocks = document.querySelectorAll('.clock, .clockutc'), i = 0, l = clocks.length;
for (; i < l; i++) {
    if (clocks[i].classList.contains('clockutc')) {
        new Clock(clocks[i], -7); // Set offset to -7 hours for clockutc
    } else {
        new Clock(clocks[i]); // Default offset (local time) for other clocks
    }
}


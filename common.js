// javascript routines common to multiple apps

var relayURL = 'http://192.168.0.56:8076/'
//~ var relayURL = 'http://k7uop.fom-az.net:8076/'
		
function Slice(num, freq, active, tx) {
	this.slice_num = num;
	this.freq = freq;
	this.active = active;
	this.tx = tx;
}

function Relay(pin, state, onLabel, offLabel) {
	this.pin = pin;
	this.state = state;
	this.onLabel = onLabel;
	this.offLabel = offLabel;
}
		
function getSlices(callback) {
	$.ajax({url:"../get_slices.py",
			cache: false,
			type: "GET",
			success: function(data) {
				if (data.length > 1) {
					tmplist = data.split('\n');
					slices = [];
					for (i=1;i<tmplist.length-1;i++) {
						t = tmplist[i].split(',');
						slices.push(new Slice(t[0], t[1], t[2], t[3]));
					}
					callback(true);
				}
				else {
					callback(false);
				}
			},
			error: function(xhr) {
				alert("ERROR in getSlices" + xhr);
				callback(false);
			}
	});
}


function startRelayControl(callback, func, cmd, pin) {
	$.ajax({url:'../relay_control.cgi',
			data: cmd,
			cache: false,
			type: "GET",
			success: function(data) {
				setTimeout(function() {
						relayControl(callback, func, pin, 'na');
					}
					, 2000);
			},
			error: function(xhr) {
				alert("ERROR in startRelayControl: " + xhr);
			}
	});
}

// func=exec|status|get_relays   pin=NameOfRelayPin   cmd=on|off
function relayControl(callback, func, pin, cmd) {
	$.ajax({url:relayURL + func,
			cache: false,
			data: {'cmd':cmd, 'pin':pin},
			type: "GET",
			success: function(data) {
				callback(pin, data);
			},
			error: function(xhr) {
				if (confirm('RelayControl Probably NOT Running.\n' +
						'Do You want to Start it?')) {
					startRelayControl(callback, func, 'start', pin);
				}
			}
	});
}

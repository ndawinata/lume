let latMax = 5
let latMin = -11
let lonMax = 142
let lonMin = 94


const loadLocCache = () => {
    const latitude = ur_lat;
    const longitude = ur_lon;
    const radius = r;
    
    if (latitude && longitude && radius) {
        return [latitude,longitude,radius]
    } else {
        // getLocation()
        return null
    }
}

function showBox(mmi,params,R,ot) {
    $("#boxmmi").show();  // Shows the box
    $("#mmi").text(mmi)
    $("#params").html(params)
    $("#ot1").text(moment.utc(ot).format("DD MMM YYYY"))
    $("#ot2").text(moment.utc(ot).format("hh:mm:ss UTC"))

    let ct = countTime(R, ot)
    $(".est").text(`${ct}s`);
    let s = ct
    const countdown = setInterval(() => {
        if (s <= 0) {
            $("#dtk").text(0); // Display 0 when countdown reaches 0
            clearInterval(countdown); // Stop the interval
            hideBox()
        } else {
            $("#dtk").text(s--); // Continue countdown
        }
    }, 1000);
}

// Function to hide the box
function hideBox(mmi,params) {
    setTimeout(()=>{
        $("#boxmmi").hide();  // Hides the box
        $("#mmi").text(null)
        $("#params").text(null)
        $("#dtk").text(null)
        $(".est").text(null);
    },3*60*1000)
}

const countTime = (distance, ot) => {
    let st = moment.utc()
    let ctd = Math.round(distance / 4)
    let ct1 = moment.utc(ot)
    
    let ct3 = Math.round(moment.duration(st.diff(ct1)).asSeconds())
    
    if(ctd - ct3 < 0){
        return 0
    }else{
        return ctd -ct3
    }
}


let lokasiDevice = loadLocCache()

var activeData = null;
    
coorEvent = lokasiDevice ? lokasiDevice : [0.7893, 113.9213]
var map = L.map('map', {
    center: coorEvent,
    zoomControl: false,
    zoom: 6,
    attributionControl: false,
})
    
var myAttrControl = L.control.attribution().addTo(map);
myAttrControl.setPrefix('<a href="https://leafletjs.com/">Leaflet</a>');
    
var layerGroup = L.layerGroup();
    
layerGroup.addLayer(L.tileLayer('https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases" title="CyclOSM - Open Bicycle render">CyclOSM</a> | Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}));
    
    
layerGroup.addTo(map);
    

$('#saveLocation').click(function() {
        var latitude = $('#latitude1').val();
        var longitude = $('#longitude1').val();
        var radius = $('#radius1').val();
        // console.log(latitude, longitude)

        // Check if the values are filled
        if (latitude && longitude && radius) {
            fetch('/set_coor', {
                method: 'POST', // Metode HTTP
                headers: {
                    'Content-Type': 'application/json' // Tipe konten yang dikirim
                },
                body: JSON.stringify({
                    "ur_lat":latitude,
                    "ur_lon":longitude,
                    "r":radius,
                }) // Data yang dikirim
            })

          // Hide the modal after saving
          $('#locationModal').modal('hide');
          
          alert('Location saved successfully!');
          setTimeout(function() {
            location.reload();
        }, 1000);
        } else {
          alert('Please fill in all fields.');
        }
});
    
    

$('#focusIcon').click(function() {
        
    let lat1 = ur_lat;
    let lon1 = ur_lon;
    let radius = r;
        
    $('#latitude1').val(lat1);
    $('#longitude1').val(lon1);
    $('#radius1').val(radius);
    $('#locationModal').modal('show');
          
});

$('#settingIcon').click(function() {
    window.location.href = '/setting';       
});

function getRectangleCoordinates(lat, lng, radiusDeg) {
        var rlon = (radiusDeg / 2) + radiusDeg
        var latMin = lat - radiusDeg;
        var latMax = lat + radiusDeg;
        var lngMin = lng - radiusDeg;
        var lngMax = lng + radiusDeg;
        // var lngMin = lng - rlon;
        // var lngMax = lng + rlon;
  
        return [[latMin, lngMin], [latMax, lngMax]];
}
    

const initLoc = (position) => {
        let loc = loadLocCache()
        if (loc){
            var bounds = getRectangleCoordinates(parseFloat(loc[0]), parseFloat(loc[1]), parseFloat(loc[2]))
            latMax = bounds[1][0]
            latMin = bounds[0][0]
            lonMax = bounds[1][1]
            lonMin = bounds[0][1]

            L.rectangle(bounds, {
                color: '#0D47A1',    // Warna garis biru
                weight: 2,        // Ketebalan garis
                fillOpacity: 0    // Transparansi di bagian tengah
            }).addTo(map);

            var bounds = [
                [latMin, lonMin], // Southwest (barat daya)
                [latMax, lonMax]   // Northeast (timur laut)
              ];
          
              // Set view berdasarkan bounds
            map.fitBounds(bounds);

        }else{
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition((position)=>{
                    let lat1 = position.coords.latitude;
                    let lon1 = position.coords.longitude;
        
                    $('#latitude1').val(lat1);
                    $('#longitude1').val(lon1);
                    $('#locationModal').modal('show');
                })
            }

        }

}

    
initLoc()
    
const showError = (error) => {
        switch(error.code) {
            case error.PERMISSION_DENIED:
                alert("User denied the request for Geolocation.");
                break;
            case error.POSITION_UNAVAILABLE:
                alert("Location information is unavailable.");
                break;
            case error.TIMEOUT:
                alert("The request to get user location timed out.");
                break;
            case error.UNKNOWN_ERROR:
                alert("An unknown error occurred.");
                break;
        }
}
    
const protocol = window.location.protocol;
const host = window.location.host;
const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
    
var apiUrlHist = `${protocol}//${host}/history`;
var apiFeedback = `https://simap.bmkg.go.id/feedback`;
var wsData = `${wsProtocol}//${host}/ws_data`; // Sesuaikan dengan URL server WebSocket Anda
    
let listHis = []
let datMinMap = {}
let histId = null
let idxHist = 0
let starK = L.icon({
    iconUrl: "static/img/starK.svg",
    iconSize: [38, 38],
});

let starM = L.icon({
    iconUrl: "static/img/starM.svg",
    iconSize: [38, 38],
});

let pulseIcon = L.icon.pulse({ iconSize: [12, 12], color: 'red' });
    
    
let wordenMMI = (pga) => {
    if (Math.log10(pga) <= 1.57) {
        return Math.ceil(1.78 + 1.55 * Math.log10(pga));
    } else {
        return Math.ceil(-1.6 + 3.7 * Math.log10(pga));
    }
};
    
   
var layerEvent = L.layerGroup().addTo(map);
    
    
function clearLayer(layer) {
    layer.clearLayers();
}
    
    
sicon = 44
var pinloc = L.icon({
    iconUrl: "/static/img/loc.gif",
    iconSize: [sicon, sicon],
    iconAnchor: [sicon/2, sicon-2]
});
    
    
lokasiDevice ? L.marker(lokasiDevice, { icon: pinloc }).bindPopup(`<div class="text-center"><b>My Location</b></div><div class="text-center">${ur_lat}, ${ur_lon}</div><div class="text-center">${lok}</div>`).addTo(map) : null
    
var audio = document.getElementById('myAudio');
var bell = document.getElementById('bell');
    
var websocket2;
var reconnectInterval = 10000; // 10 detik
    
function WS_Data() {
    websocket2 = new WebSocket(wsData);
    
    websocket2.onopen = function (evt) {
        // console.log("Connected to WebSocket2");
        $('.ws2').removeClass('fa-times-circle').removeClass('red-color').addClass('fa-check-circle green-color');
    };
    
    websocket2.onclose = function (evt) {
        // console.log("Disconnected from WebSocket, trying to reconnect...");
        $('.ws2').removeClass('fa-check-circle').removeClass('green-color').addClass('fa-times-circle red-color');
        setTimeout(WS_Data, reconnectInterval);
    };
    
    websocket2.onmessage = function (evt) {
        let dd = JSON.parse(evt.data)

        // console.log(dd)

        let tipe = dd.earthquake.type
        let data = dd.earthquake.event

        if (tipe == 'report') {
            layerEvent.clearLayers();

            L.marker([data.latitude, data.longitude], { icon: pulseIcon }).addTo(layerEvent);
    
            L.marker([data.latitude, data.longitude], {
                icon: starM
            }).bindPopup(`
            <div class="tb">
                <div class="fw-bold kode bg-danger text-white" >Earthquake Report</div>
                    <div style="margin:10px">
                        <table class="tbl">
                            <tr>
                                <td class="fw-bold">Id</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.id}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Origintime</td>
                                <td class="fw-bold ">:</td>
                                <td>${moment.utc(data.originTime).format("DD-MM-YY HH:mm:ss UTC")}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Magnitude</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.magnitude}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Depth</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.depth} Km</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Epic</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.latitude}, ${data.longitude}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Address</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.localAddress}</td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
            `).addTo(layerEvent)

            map.setView([data.latitude, data.longitude], 7);

            setTimeout(() => {
                layerEvent.clearLayers();
                map.setView([ur_lat, ur_lon], 5);
            }, 60 * 5 * 1000)
            
        } 
        if (tipe == 'alert') {
            const coord1 = L.latLng(data.latitude, data.longitude);
            const coord2 = L.latLng(ur_lat, ur_lon);

            R = coord1.distanceTo(coord2) / 1000

            if (dd.earthquake.impact !== undefined) {
                showBox(dd.earthquake.impact.mmi, `Mag: <span class="txtblue"> ${data.magnitude} </span> depth: <span class="txtblue"> ${data.depth} </span> km`,R, data['originTime'])
            }


            layerEvent.clearLayers();
            
            L.marker([data.latitude, data.longitude], { icon: pulseIcon }).addTo(layerEvent);

            L.marker([data.latitude, data.longitude], {
                icon: starK
            }).bindPopup(`
            <div class="tb">
                <div class="fw-bold kode bg-warning text-dark">Earthquake Alert</div>
                    <div style="margin:10px">
                        <table class="tbl">
                            <tr>
                                <td class="fw-bold">Id</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.id}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Origintime</td>
                                <td class="fw-bold ">:</td>
                                <td>${moment.utc(data.originTime).format("DD-MM-YY HH:mm:ss UTC")}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Magnitude</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.magnitude}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Depth</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.depth} Km</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Epic</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.latitude}, ${data.longitude}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Address</td>
                                <td class="fw-bold ">:</td>
                                <td>${data.localAddress}</td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
            `).addTo(layerEvent)

            if(dd.earthquake.multipoint){
                dd.earthquake.multipoint.map((ddt)=>{
                    let nm = ddt.name
                    let nmmi = ddt.mmi
                    let npga = ddt.pga
                    let latlng = [ddt.lat, ddt.lon]
                    if (nmmi == 1) {
                        L.marker(latlng, { icon: int1 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent);
                    } else if (nmmi == 2) {
                        L.marker(latlng, { icon: int2 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    } else if (nmmi == 3) {
                        L.marker(latlng, { icon: int3 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    } else if (nmmi == 4) {
                        L.marker(latlng, { icon: int4 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    } else if (nmmi == 5) {
                        L.marker(latlng, { icon: int5 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    } else if (nmmi == 6) {
                        L.marker(latlng, { icon: int6 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    } else if (nmmi == 7) {
                        L.marker(latlng, { icon: int7 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    } else if (nmmi == 8) {
                        L.marker(latlng, { icon: int8 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    } else if (nmmi == 9) {
                        L.marker(latlng, { icon: int9 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    }else if (nmmi == 10) {
                        L.marker(latlng, { icon: int10 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    }else if (nmmi == 11) {
                        L.marker(latlng, { icon: int11 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    }else if (nmmi == 12) {
                        L.marker(latlng, { icon: int12 }).bindPopup(`Name : ${nm} <br>pga:  ${npga}`).addTo(layerEvent)
                    }
                })
            }

    
            map.setView([data.latitude, data.longitude], 7);
    
            setTimeout(() => {
                layerEvent.clearLayers();
                map.setView([ur_lat, ur_lon], 7);
            }, 60 * 5 * 1000)
            

        } 
        if (tipe == 'ws_svr'){
            if(data){
                $('.ws1').removeClass('fa-times-circle').removeClass('red-color').addClass('fa-check-circle green-color');
            }else{
                $('.ws1').removeClass('fa-check-circle').removeClass('green-color').addClass('fa-times-circle red-color');
            }
        }
    
    };
    
    websocket2.onerror = function (evt) {
        $('.ws2').removeClass('fa-check-circle').removeClass('green-color').addClass('fa-times-circle red-color');
        setTimeout(WS_Data, reconnectInterval);
    };
    
}

// const getArea = async (lat, lon) => {
//     // console.log(lat, lon)
//     const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}`);
//     const data = await response.json();

//     let txt = data.display_name;
//     if(txt){
//         let array = txt.split(", ");

//         // Mengecek dua index terakhir
//         let lastIndex = array.length - 2; // Index terakhir
//         let secondLastIndex = lastIndex - 1; // Index kedua terakhir
        
//         // Mengecek apakah index pertama dari dua terakhir adalah angka
//         if (!isNaN(array[secondLastIndex])) {
//             // Jika ya, ambil index ketiga terakhir dan kedua terakhir (tanpa angka)
//             return [array[lastIndex - 2], array[lastIndex]].toString();
//         } else {
//             // Jika tidak, ambil kedua index terakhir
//             return [array[secondLastIndex], array[lastIndex]].toString();
//         }
//     }else{
//         return "-"
//     }
// }

const getArea = async (lat, lon) => {
    try {
        const response = await fetch(`/rev_geocoding/${lat},${lon}`);
        const data = await response.json();

        return data.lokasi
    } catch (error) {
        console.error("Error fetching area:", error);
        return "--";
    }
};

const table = $('#historyTable').DataTable({
    data: [], // Data awal kosong
    columns: [
        { title: "No" },
        { title: "OriginTime" },
        { title: "Latitude" },
        { title: "Longitude" },
        { title: "Magnitude" },
        { title: "Depth" },
        { title: "Area" },
        { title: "Source" },
        { 
            title: "Action",
                render: function (data, type, row) {
                    return `<button class="btn btn-primary" onclick="window.open('/detail/${row[8]}', '_blank')">
                                Detail
                            </button>`;
                }
         }
    ],
    "columnDefs": [
            {
                "targets": 0, 
                "orderable": false, 
                "searchable": false, 
                "render": function (data, type, row, meta) {
                    return meta.row + 1; 
                }
            }
        ]
});



var apiUrlHist = `${protocol}//${host}/history`;

async function fetchData() {
    try {
        const response = await fetch(apiUrlHist);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        // Format data untuk DataTable dengan area diambil secara asinkron
        const formattedData = await Promise.all(
            data.map(async item => {
                let area = "";
                if (item.pgn) {
                    area = await getArea(item.pgn.lat, item.pgn.lon);
                } else {
                    area = await getArea(item.eew.lat, item.eew.lon);
                }

                return [
                    null,
                    moment.utc(item.ot).format("DD-MM-YY HH:mm:ss UTC") || '',
                    item.pgn ? item.pgn.lat : item.eew.lat,
                    item.pgn ? item.pgn.lon : item.eew.lon,
                    item.pgn ? item.pgn.mag: item.eew.mag,
                    item.pgn ? item.pgn.depth : item.eew.depth,
                    area,
                    item.pgn ? "Report" : "Alert",
                    item.id
                ];
            })
        );

        // Reset tabel dan tambahkan data baru
        table.clear();
        table.rows.add(formattedData);
        table.draw();
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

    
WS_Data()

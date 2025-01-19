const protocol = window.location.protocol;
const host = window.location.host;
    
var apiUrl = `${protocol}//${host}/`;

let dat = {}
let starK = L.icon({
    iconUrl: apiUrl + "static/img/starK.svg",
    iconSize: [38, 38],
});

let starM = L.icon({
    iconUrl: apiUrl + "static/img/starM.svg",
    iconSize: [38, 38],
});

coord = data['pgn'] ? [data['pgn']['lat'], data['pgn']['lon']] : [data['eew']['lat'], data['eew']['lon']]

var map = L.map('map', {
    center: coord,
    zoomControl: false,
    zoom: 8,
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

let eventLayer = L.layerGroup().addTo(map);
let layerPga = L.layerGroup().addTo(map);
let layerMMI = L.layerGroup().addTo(map);
let layerFeed = L.layerGroup().addTo(map);
let layerCountur = L.layerGroup().addTo(map);

function clearLayer(layer) {
    layer.clearLayers();
}

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


if (data['eew']){
    let pulseIcon = L.icon.pulse({ iconSize: [9, 9], color: '#FFC847' });

    dat['lat'] = data['eew']['lat']
    dat['lon'] = data['eew']['lon']
    dat['mag'] = data['eew']['mag']
    dat['area'] = "-"
    dat['depth'] = data['eew']['depth']
    dat['ot'] = data['eew']['ot']
    dat['id'] = data['eew']['eew_id']

    $("#wkt").text(moment(data['eew']['originTime']).format('DD-MM-YYYY HH:mm:ss') + " UTC")
    
    L.marker(coord, { icon: pulseIcon }).addTo(eventLayer);
    getArea(dat['lat'], dat['lon'])
        .then(lok=>{
            L.marker(coord, { icon: starK }).bindPopup(`
                    <div class="tb">
                        <div class="fw-bold kode bg-warning text-dark">Earthquake Alert</div>
                            <div style="margin:10px">
                                <table class="tbl">
                                    <tr>
                                        <td class="fw-bold">Id</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${dat['id']}</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Origintime</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${moment.utc(dat['ot']).format("DD-MM-YY HH:mm:ss UTC")}</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Magnitude</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${dat['mag']}</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Depth</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${dat['depth']} Km</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Epic</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${dat['lat']}, ${dat['lon']}</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Address</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${lok}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    </div>
            `).addTo(eventLayer).openPopup();
        })
}

if (data['pgn']) {
    let pulseIcon = L.icon.pulse({ iconSize: [9, 9], color: 'red' });

    dat['lat'] = data['pgn']['lat']
    dat['lon'] = data['pgn']['lon']
    dat['mag'] = data['pgn']['mag']
    dat['depth'] = data['pgn']['depth']
    dat['ot'] = data['pgn']['ot']
    dat['id'] = data['pgn']['pgn_id']

    $("#wkt").text(moment(data['pgn']['ot']).format('DD-MM-YYYY HH:mm:ss') + " UTC")

    L.marker(coord, { icon: pulseIcon }).addTo(eventLayer);
    getArea(dat['lat'], dat['lon'])
        .then(lok=>{
            L.marker(coord, { icon: starM }).bindPopup(`
                    <div class="tb">
                        <div class="fw-bold kode bg-danger text-white">Earthquake Report</div>
                            <div style="margin:10px">
                                <table class="tbl">
                                    <tr>
                                        <td class="fw-bold">Id</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${dat['id']}</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Origintime</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${moment.utc(dat['ot']).format("DD-MM-YY HH:mm:ss UTC")}</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Magnitude</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${dat['mag']}</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Depth</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${dat['depth']} Km</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Epic</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${dat['lat']}, ${dat['lon']}</td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold">Address</td>
                                        <td class="fw-bold ">:</td>
                                        <td>${lok}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                    </div>
            `).addTo(eventLayer).openPopup();
        })
    
}

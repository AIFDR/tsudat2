var app;
Ext.onReady(function() {
    app = new gxp.Viewer({
        portalConfig: {
            renderTo: document.body,
            layout: "border",
            height: 600, 
            autoWidth: true,
            items: [{
                // a TabPanel with the map and a dummy tab
                id: "centerpanel",
                xtype: "tabpanel",
                region: "center",
                activeTab: 0, // map needs to be visible on initialization
                border: true,
                items: ["map"]
            }, {
                // container for the queryform
                id: "west",
                xtype: "container",
                layout: "fit",
                region: "west",
                width: 200
                }],
            bbar: {id: "bbar"}
        },
        defaultSourceType: "gx_wmssource",
        sources: {
            osm: {
                ptype: "gxp_osmsource"
            },
            local: {
                url: "/geoserver-geonode-dev/wms",
                ptype: "gxp_wmssource"
            },
        },
        tools: [{
            ptype: "gxp_layertree",
            outputConfig: {
                id: "tree",
                border: true,
                tbar: [] // we will add buttons to "tree.bbar" later
            },
            outputTarget: "west"
        }, {
            ptype: "gxp_addlayers",
            actionTarget: "tree.tbar"
        }, {
            ptype: "gxp_removelayer",
            actionTarget: ["tree.tbar", "tree.contextMenu"]
        }, {
            ptype: "gxp_zoomtoextent",
            actionTarget: "map.tbar"
        }, {
            ptype: "gxp_zoom",
            actionTarget: "map.tbar"
        }, {
            ptype: "gxp_navigationhistory",
            actionTarget: "map.tbar"
        }, {
            ptype: "gxp_wmsgetfeatureinfo",
            outputConfig: {
                width: 400,
                height: 200
            },
            actionTarget: "map.tbar", // this is the default, could be omitted
            toggleGroup: "layertools"
        }],
        
        map: {
            id: 'map',
            title: "Map",
            projection: "EPSG:900913",
            units: "m",
            maxResolution: 156543.0339,
            center: [14903596.860493, -2716710.1766439],
            zoom: 3,
            layers: [{
                source: "osm",
                name: "mapnik"
            }, {
                source: "local",
                name: "tsudat:tsudat_hazardpoint",
                selected: true
            }, {
                source: "local",
                name: "tsudat:tsudat_subfault",
                selected: true
            }]
        }
    });
});

WEB_SOCKET_SWF_LOCATION = "{{ url_for('explorer.static', filename='WebSocketMain.swf')}}";
WEB_SOCKET_DEBUG = true;

// socket.io specific code
var socket = io.connect('/explorer');

//globals
var chart;

socket.on('files', function(directory, files){
    var files_temp = []
    for (var i=0; i<files.length; i++){
        files_temp.push({name: files[i]});
    }
    switch(directory) {
        case "experiments":
            expDirModel.newItems(files_temp);
            break;
        case "analysis":
            analysisModel.newItems(files_temp);
            node = $('#folder_tree').jstree(true).get_node('analysis')
            $('#folder_tree').jstree(true).rename_node(node, 'Analysis ' + files_temp.length)
            break;
        case "manual":
            manualModel.newItems(files_temp);
            node = $('#folder_tree').jstree(true).get_node('manual')
            $('#folder_tree').jstree(true).rename_node(node, 'Manual ' + files_temp.length)
            break;
        case "raw_dat":
            raw_datModel.newItems(files_temp);
            node = $('#folder_tree').jstree(true).get_node('raw_dat')
            $('#folder_tree').jstree(true).rename_node(node, 'Raw ' + files_temp.length)
            break;
        case "avg":
            avgModel.newItems(files_temp);
            node = $('#folder_tree').jstree(true).get_node('avg')
            $('#folder_tree').jstree(true).rename_node(node, 'Average ' + files_temp.length)
            break;
        case "finished":
            $('body').toggleClass('loading');
            
    }
})

socket.on('data', function(data) {
    
    if (chart.series.length > data.length) {
        for (i=chart.series.length-1;i>=data.length;i--) {
            console.log(i);
            chart.series[i].remove(false);
        }
    }
    
    for (i=0;i<data.length;i++) {
        
        if (i < chart.series.length) {
            chart.series[i].name = data[i].name;
            chart.series[i].setData(data[i].data, false);    
        } else {
            chart.addSeries({
                name: data[i].name,
                data: data[i].data,
                downsample: { threshold: 0}
                },
                false);
        }
    }
    
    chart.redraw();
    
});

/* File/Folder Selection Code */

var itemModel = function(item){
    var self = this;

    self.item = item;
    self.selected = ko.observable(false);
    self.visible = ko.observable(true);

    self.set_select = function(value){
        self.selected(value);
    };

    self.selectedCSS = ko.computed(function(){
        if (self.selected()) { return "selected" }
        return ""
    });
    
    self.set_visibile = function(visible){
        self.visible(visible);
    };
};

var itemListModel = function(items, multiselect) {
    var self = this;

    self.filter_input = ko.observable("");
    
    multiselect = (typeof multiselect === 'undefined') ? false : multiselect;

    var itemObjs = [];
    for (var i=0; i<items.length; i++){
        itemObjs.push(new itemModel(items[i]));
    }

    self.items = ko.observableArray(itemObjs);
    
    self.newItems = function(items) {
        itemObjs = [];
        for (var i=0; i<items.length; i++){
            itemObjs.push(new itemModel(items[i]));
        }
        self.items([]);
        self.items(itemObjs);
    };

    self.addItem = function() {
        self.items.push({
            name: ""
        });
    };

    self.removeItem = function(item) {
        self.items.remove(item);
    };

    self.select = function(item){
        selectedList = self.itemList();
        selected = item.selected()

        if (event.shiftKey && multiselect) {
            if (!event.ctrlKey) {
                selectedList.forEach(function(element){
                    if (item != element) {element.set_select(false)}
                });
            }
            startIndex = $.inArray(self.lastselected,self.items());
            endIndex = $.inArray(item,self.items());
            for (i=Math.min(startIndex,endIndex);i <= Math.max(startIndex,endIndex); i++){
                self.items()[i].set_select(true);
            }
        } else {
            self.lastselected = item;
            if (event.ctrlKey && multiselect) {
                item.set_select(!selected);
            } else {
                selectedList.forEach(function(element){
                    if (item != element) {element.set_select(false)}
                });
                item.set_select(!selected);
            }
        }
    };
    
    self.filter = function(filter) {
        self.items().forEach(function(i){
            i.set_visibile(~i.item.name.indexOf(filter))
        });
    }

    ko.computed(function(){
       self.filter(self.filter_input());
    });
    
    self.itemList = ko.computed(function(){
        selectedList =[];
        self.items().forEach(function(item){
            if (item.selected()) {selectedList.push(item) }
        });
        return selectedList
    });

};

var profile_loader = function(item, multiselect, directory) {
    var self = this;
    self.div_visible = ko.observable(false);
    itemListModel.call(self, item, multiselect);
    self.send = function(item){
        self.select(item);
        names = [];
        self.itemList().forEach(function(i){
            names.push(i.item.name)
        });
        socket.emit('load_dat',names, directory);
    };
    self.set_div_visible = function(visible){
        self.div_visible(visible);
    }
};

var expDirModel = new itemListModel([], false);

var analysisModel = new profile_loader([], true, 'analysis');
var manualModel = new profile_loader([], true, 'manual');
var raw_datModel = new profile_loader([], true, 'raw_dat');
var avgModel = new profile_loader([], true, 'avg');


var sendExpDirList = function(){
    var expDirs = []
    expDirModel.itemList().forEach(function(element){
        expDirs.push(element.item.name);
    });
    socket.emit('open_experiment', expDirs);
    $('body').toggleClass('loading');
};


$(function() {

    $(document).ready( function() {
        /* Chart */
        chart = new Highcharts.Chart({
            chart: {
                renderTo: 'container',
                type: 'scatter'
            },
            title: {
                text: 'SAXS Profile',
            },
            xAxis: {
                title: {
                    text: 'q'
                },
                type: 'logarithmic'
            },
            yAxis: {
                title: {
                    text: 'Intensity'
                },
                type: 'logarithmic'
            },
            series: [{
                name: 'Profile',
                data: [],
                downsample: { threshold: 200}
            }]
            
        });
    });

    /* Select Experiment Dialog */
    $("#SelectExperimentsDialog").dialog({
            autoOpen: true,
            modal: true,
            height: 850,
            width: 800,
            open: function(event,ui){
                $(this).css('overflow','hidden');
            },
            buttons: {
                "OK!": function() {
                    if (expDirModel.itemList().length < 1) {
                        display_message({message: "Please Choose an experiment.", title: "Choose an experiment!!"});
                        return;
                    }
                    $(this).dialog("close");
                    sendExpDirList();
                },
                "Cancel": function() {
                    $(this).dialog("close");
                }
            }
        });

    /* Folder Tree */
    $('#folder_tree')
        // listen for event
        .on('select_node.jstree', function(e, data){ 
            
            avgModel.set_div_visible(data.node.id=='avg');
            analysisModel.set_div_visible(data.node.id=='analysis');
            manualModel.set_div_visible(data.node.id=='manual');
            raw_datModel.set_div_visible(data.node.id=='raw_dat');
            
        })
        .jstree({ 'core' : {
        'data' : [
            {id : 'avg', text : 'Average'},
            {id : 'analysis', text : 'Analysis'},
            {id : 'manual', text : 'Manual'},
            {id : 'raw_dat', text : 'Raw'}
        ],
        check_callback: true
    }});
    
    ko.applyBindings(expDirModel, document.getElementById("SelectExperimentsDialog"));
    
    ko.applyBindings(analysisModel, document.getElementById("analysis"));
    ko.applyBindings(manualModel, document.getElementById("manual"));
    ko.applyBindings(raw_datModel, document.getElementById("raw_dat"));
    ko.applyBindings(avgModel, document.getElementById("avg"));
    
});

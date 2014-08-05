WEB_SOCKET_SWF_LOCATION = "{{ url_for('explorer.static', filename='WebSocketMain.swf')}}";
WEB_SOCKET_DEBUG = true;

// socket.io specific code
var socket = io.connect('/explorer');

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
            break;
        case "manual":
            manualModel.newItems(files_temp);
            break;
        case "raw_dat":
            raw_datModel.newItems(files_temp);
            break;
    }
})

/* File/Folder Selection Code */

var itemModel = function(item){
    var self = this;

    self.item = item;
    self.selected = ko.observable(false);

    self.set_select = function(value){
        self.selected(value);
    };

    self.selectedCSS = ko.computed(function(){
        if (self.selected()) { return "selected" }
        return ""
    });
};

var itemListModel = function(items, multiselect) {
    var self = this;

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

    self.itemList = ko.computed(function(){
        selectedList =[];
        self.items().forEach(function(item){
            if (item.selected()) {selectedList.push(item) }
        });
        return selectedList
    });

};

var expDirModel = new itemListModel([], false);

var analysisModel = new itemListModel([], true);

var manualModel = new itemListModel([], true);

var raw_datModel = new itemListModel([], true);


var sendExpDirList = function(){
    var expDirs = []
    expDirModel.itemList().forEach(function(element){
        expDirs.push(element.item.name);
    });
    socket.emit('open_experiment', expDirs);
};


$(function() {


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
                    console.log(analysisModel.items())
                    if (expDirModel.itemList().length < 1) {
                        display_message({message: "Please Choose an experiment.", title: "Choose an experiment!!"});
                        return;
                    }
                    $(this).dialog("close");
                    $('body').toggleClass('loading');
                    sendExpDirList();
                },
                "Cancel": function() {
                    $(this).dialog("close");
                }
            }
        });

    /* Left Hand Navigation Tabs */
    $( "#LHTabs" ).tabs();


    ko.applyBindings(expDirModel, document.getElementById("SelectExperimentsDialog"));
    ko.applyBindings(analysisModel, document.getElementById("analysis"));
    ko.applyBindings(manualModel, document.getElementById("manual"));
    ko.applyBindings(raw_datModel, document.getElementById("raw_dat"));
});

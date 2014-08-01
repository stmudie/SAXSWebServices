WEB_SOCKET_SWF_LOCATION = "{{ url_for('gradientprofiles.static', filename='WebSocketMain.swf')}}";
WEB_SOCKET_DEBUG = true;

function zip(arrays) {
    return arrays[0].map(function(_,i){
        return arrays.map(function(array){return array[i]})
    });
}

function isNumberKey(evt,id) {
            var charCode = (evt.which) ? evt.which : event.keyCode;
                if (charCode != 46 && charCode != 45 && charCode > 31 && (charCode < 48 || charCode > 57)) {
                $('#'+id).css("background","rgb(255,0,0)");
                setTimeout(function(){$('#'+id).css("background","rgb(255,255,255)")},200);
                return false;
            } else if (charCode == 46) {
                if ($.inArray('.',$('#'+id).val()) == -1 ) {
                    return true;
                } else {
                    $('#'+id).css("background","rgb(255,0,0)");
                    setTimeout(function(){$('#'+id).css("background","rgb(255,255,255)")},200);
                    return false;
                }

            } else {
                return true;
            }
        };

function display_message(message) {
    var messageDialog = $("#MessageDialog")
    messageDialog.text(message.message);
    messageDialog.dialog("option", "title", message.title);
    messageDialog.dialog("open");
}

var sample_data = [];
var buffer_data = [];
var newData = [];
var lastselectedsample ='';

var fileModel = function(file){
    var self = this;

    self.file = file;
    self.sample = ko.observable(false);
    self.buffer = ko.observable(false);

    self.setselect = function(type,value){
        if (type == 'buffer') {self.buffer(value)} else if (type == 'sample') {self.sample(value)};
    }

    self.selectedCSS = ko.computed(function(){
        if (self.sample() && !self.buffer()) { return "sampleselect" }
        if (!self.sample() && self.buffer()) { return "bufferselect" }
        if (self.sample() && self.buffer()) { return "sampleselect bufferselect" }
        return ""
    });
}

var fileListModel = function(files) {
    var self = this;

    fileObjs = [];
    for (i=0;i<files.length;i++){
    fileObjs.push(new fileModel(files[i]));
    }
    self.files = ko.observableArray(fileObjs);


    self.newFiles = function(files) {
    fileObjs = [];
    for (i=0;i<files.length;i++){
        fileObjs.push(new fileModel(files[i]));
    }
    self.files([]);
    self.files(fileObjs);
    }

    self.addFile = function() {
        self.files.push({
            name: ""
        });
    };

    self.removeFile = function(file) {
        self.files.remove(file);
    };

    self.select = function(file,event){
        if ($(event.target).hasClass('sample')) {
            selectedList = self.sampleList();
            type = 'sample';
            selected = file.sample()
        } else if ($(event.target).hasClass('buffer')) {
            selectedList = self.bufferList();
            type = 'buffer';
            selected = file.buffer()
        }

        multiselect = false;

        if (event.shiftKey && multiselect) {
            if (!event.ctrlKey) {
                selectedList.forEach(function(item){
                    if (file != item) {item.setselect(type,false)}
                });
            }
            startIndex = $.inArray(self.lastselected,self.files());
            endIndex = $.inArray(file,self.files());
            for (i=Math.min(startIndex,endIndex);i <= Math.max(startIndex,endIndex); i++){
                self.files()[i].setselect(type,true);
            }
        } else {
            self.lastselected = file;
            if (event.ctrlKey && multiselect) {
                file.setselect(type,!selected);
            } else {
                selectedList.forEach(function(item){
                    if (file != item) {item.setselect(type,false)}
                });
                file.setselect(type,!selected);
            }
        }
    };

    self.sampleList = ko.computed(function(){
        selectedList =[];
        self.files().forEach(function(file){
            if (file.sample()) {selectedList.push(file) };
        });
        return selectedList
    });

    self.bufferList = ko.computed(function(){
        selectedList =[];
        self.files().forEach(function(file){
            if (file.buffer()) {selectedList.push(file) };
        });
        return selectedList
    });

};


var myViewModel = new fileListModel([

]);

var sendFileList = function(){
    samples = [];
    buffers = [];
    myViewModel.sampleList().forEach(function(element){
        samples.push(element.file.name);
    });
    myViewModel.bufferList().forEach(function(element){
        buffers.push(element.file.name);
    });
    socket.emit('openfile', samples, buffers);
};


var highqSettings = {
    chart: {
        renderTo: 'dummy',
        type: 'scatter',
        zoomType: 'xy',
        backgroundColor: '#F2F2F2',
        animation: false
    },
    title: {
        text: 'High q'
    },
    xAxis: {
        title: {
            enabled: true,
            text: 'File Index'
        },
        type: 'linear',
        gridLineWidth: 1,
        //tickInterval: 1,
        //minorTickInterval: 0.1,
        startOnTick: false,
        endOnTick: false,
        showLastLabel: true
    },
    yAxis: { //Primary Y Axis
        title: {
            text: 'I High Q (cm-1)',
            style: {
                color: '#1BA01D'
            }
        },
        gridLineWidth: 1,
        startOnTick: true,
        endOnTick: true,
        style: {
            color: '#BC1414'
        }
    },
    plotOptions: {
        series: {
            cursor: 'move',
            point: {
                events: {
                    drag: function (e) {
                        xpos = highq_chart.series[0].xData.indexOf(e.target.category);
                        mult = e.newY / buffer_data[xpos][1];
                        slide = +(e.newX - buffer_data[xpos][0]).toFixed(1);
                        newData = [];
                        buffer_data.forEach(function (item) {
                            newData.push([item[0] + slide, item[1] * mult]);
                        });
                        highq_chart.series[0].setData(newData);
                        $("#BufferOffset").val(slide);
                    },
                    drop: function (e) {
                        highq_chart.series[0].setData(newData);
                    }
                }
            },
            stickyTracking: false
        }
    },
    tooltip: {
        enabled: true
    },
    series: [
        {
            name: 'Buffer',
            color: 'Green',
            draggableX: true,
            draggableY: false,
            zIndex: 1
        },
        {
            name: 'Sample',
            color:'#BC1414'
        }]
};


// socket.io specific code
var socket = io.connect('/gradientprofiles');

socket.on('connect', function () {
});

socket.on('error', function (e) {
    message('System', e ? e : 'A unknown error occurred');
});

socket.on('message', function(message){
    display_message(message);
});

socket.on('File_List', function(filelist){
    filelisttemp =[];
    for (var i=0; i<filelist.length; i++){
        filelisttemp.push({name: filelist[i][0].split('/').pop()});
    }
    myViewModel.newFiles(filelisttemp);

});

socket.on('samples', function(data) {
    sample_data = data.slice();
    highq_chart.series[1].setData(data);
});

socket.on('buffers', function(data) {
    buffer_data = data.slice();
    highq_chart.series[0].setData(data);
    extremes = highq_chart.xAxis[0].getExtremes();
    console.log(extremes.userMin)
    highq_chart.xAxis[0].setExtremes(extremes.min,extremes.max);
    extremes = highq_chart.xAxis[0].getExtremes();
    console.log(extremes.userMin)
    $('body').toggleClass('loading');
});

socket.on('progress', function(data) {
    progressText = data.title;
    progressbar = $( "#progressbar" );
    progressbar.progressbar("value", data.progress);
});

socket.on('offset',function(slide){
    newData = [];
    buffer_data.forEach(function (item) {
        newData.push([item[0] + slide, item[1]]);
    });
    highq_chart.series[0].setData(newData);
    $("#BufferOffset").val(slide);
});

socket.on('title', function(title){
   highq_chart.setTitle({text: title});
});

$(function () {

    var progressbar = $("#progressbar"),
    progressLabel = $(".progress-label");

    progressbar.progressbar({
        value: 0,
        change: function() {
            $("#dialog").dialog("open");
            progressLabel.text( progressText + progressbar.progressbar( "value" ) + "%" );
        },
        complete: function() {
            progressLabel.text( progressText + "Complete!" );
            $("#dialog").dialog("close");
        }
    });
});


$(function () {

    $(document).ready(function() {

        $(window).resize(function() {
            width = Math.min($(window).width()-300,1200)
            $("#raw_dat_div").width(width);
        });

        $(window).resize();

        highqSettings.chart.renderTo = 'raw_dat_div';
        highq_chart = new Highcharts.Chart(highqSettings);

        $( "#SelectFilesButton").button()
            .click(function(){
                $('#SelectFilesDialog').dialog("open")
            });

        $( "#SubtractButton").button()
            .click(function(){
                socket.emit("subtract", parseFloat($("#BufferOffset").val()));
            });

        $("#MessageDialog").dialog({
            autoOpen: false,
            modal: true,
            height: 100,
            width: 500
        });

        $("#dialog").dialog({
            autoOpen: false,
            modal: true,
            height: 100,
            width: 400
        });

        $("#SelectFilesDialog").dialog({
            autoOpen: false,
            modal: true,
            height: 850,
            width: 800,
            open: function(event,ui){
                $(this).css('overflow','hidden');
            },
            buttons: {
                "OK!": function() {
                    if (myViewModel.sampleList().length < 1) {
                        display_message({message: "Please Choose a sample.", title: "Choose a file!!"});
                        return;
                    }
                    if (myViewModel.bufferList().length < 1) {
                        display_message({message: "Please Choose a buffer.", title: "Choose a file!!"});
                        return;
                    }
                    $(this).dialog("close");
                    $('body').toggleClass('loading');
                    sendFileList();
                },
                "Cancel": function() {
                    $(this).dialog("close");
                }
            }
        });

        $("#Name").keyup(function(event) {
            if (event.keyCode == 13) {
                $("#SaveToo").click();
            }
        });

        $("#BufferOffset").spinner({
            step: 0.1,
            stop: function( event, ui) {
                $(this).trigger('allchanges');
            }
        }).keyup(function(event) {
            if (event.keyCode == 13) {
                $(this).trigger('allchanges');
            }
        }).on('allchanges', function(event){
            newData = [];
            slide = +parseFloat(this.value).toFixed(1);
            buffer_data.forEach(function (item) {
                newData.push([item[0] + slide, item[1]]);
            });
            highq_chart.series[0].setData(newData);
        });

        ko.applyBindings(myViewModel);
    });
});
'use strict';

var video = document.querySelector('video');
var canvas = document.querySelector('canvas');
var ctx = canvas.getContext('2d');
var localMediaStream = null;
var capturedImageURL = "";

function enableMedia(){
    navigator.getUserMedia = navigator.webkitGetUserMedia || navigator.getUserMedia;
    navigator.getUserMedia({video: true}, function(stream) {
        video.src = window.URL.createObjectURL(stream);
        localMediaStream = stream;
        video.play();
    }, function(){
        console.log("failed. please access option page.");
    });
}

function takeSnap(callback) {
    if (localMediaStream) {
        canvas.width = video.clientWidth;
        canvas.height = video.clientHeight;
        ctx.drawImage(video, 0, 0, video.clientWidth, video.clientHeight);
        capturedImageURL = canvas.toDataURL("image/png");
        document.querySelector('img').src = capturedImageURL;
        if(callback){
            callback(capturedImageURL);
        }
    }
}

function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

function sayuriAjax(url, method, data){
    var type = "GET";
    var sendData = {};
    if(data){
        sendData = $.extend(true,{},data);
    }
    if(method){
        type = method;
        if(type != "GET"){
            sendData._xsrf = getCookie("_xsrf");
        }
    }

    return $.ajax({
       type:method,
       url: url,
       data: sendData,
       dataType: "json"
   })
}

function SayuriModel() {
    var self = this;
    self.cf = new Conference(); //related to conference
    self.sayuri = new SayuriMessage(); //related to websocket with server side
    self.searchText = ko.observable("");
    self.alertMessage = ko.observable("");
    self.$alertDialog = $('#alertModal');

    self.init = function(){
        self.searchConference();
        self.sayuri.renderChart();
    }

    self.addMessages = function(){
        //add sayuri message
    }

    self.startConference = function(){
        self.cf.start(
            function(resp){
                //show conference start message or animation
                //self.searchConference();
            }
            ,function(errorMessage){
                self.alertMessage(errorMessage);
                self.$alertDialog.modal();
            }
        );
    }
    self.searchConference = function(){
        self.cf.search(self.searchText());
    }

}

function Conference(){
    var self = this;
    self.API = "/conference"
    self.API_IMAGE = "/conference/image"
    self.timer = null;
    self.conferenceName = ko.observable("");
    self.conferenceTime = ko.observable("");
    self.isOpen = ko.observable(false);
    self.conferences = ko.observableArray([]);

    self.start = function(success, error){
        console.log("begin conference (check group name and conference name)");
        var data = {"title": self.conferenceName(), "minutes": self.conferenceTime()}
        sayuriAjax(self.API, "POST", data)
        .done(function(resp){
            if(resp.conference == ""){ //error
                if(error){
                     error(resp.message);
                }else{
                    console.log(resp.message);
                }
            }else{
                self._open();
                if(success){
                    success(resp);
                }
            }
        })
    }

    self._open = function(){
        self.isOpen(true);
        self.timer = setInterval(function(){
            vm.sayuri.create()
            setTimeout(function(){
                vm.cf.sendImage();
            }, 1000);
        }, 5000);
        /*
        self.timer = setTimeout(function(){
            vm.cf.sendImage()
        }, 5000);
        */
    }

    self.sendImage = function(){
        if(self.isOpen()){//send only when conference is open
            takeSnap(function(imageUrl){
                 sayuriAjax(self.API_IMAGE, "POST", {"image": imageUrl})
            });
        }
    }

    self.end = function(){
        console.log("end conference");
        sayuriAjax(self.API, "DELETE")
        .done(function(){
            self.isOpen(false);
            self.searchConference();
            clearInterval(self.timer);
        });
    }

    self.search = function(searchText){
        sayuriAjax(self.API)
        .done(function(data){
            self.conferences.removeAll();
            data.conferences.forEach(function(c){
                self.conferences.push(c);
            })
            if(data.conference && !self.isOpen()){
                var c = data.conference;
                self._open();
                self.conferenceName(c.title)
                self.conferenceTime(c.minutes)
            }
        })
    }

}

function SayuriMessage(sayuriHost){
    var self = this;
    var host = (sayuriHost) ? sayuriHost : "localhost"
    self.targetAddress = "ws://{0}/sayurisocket".replace("{0}", host);
    self.socket = null;
    self.diaplay_range = 10
    self.messages = []; //ko.observableArray([]);
    self.chartArea = document.getElementById("chart").getContext("2d");
    self.chart = null

    self.create = function(){
        if(self.socket == null){
            self.socket = new WebSocket(self.targetAddress);
            self.socket.onopen = function() {
                console.log("connected to sayuri");
            };
            self.socket.onclose = function() {
                self.socket = null;
            };
            self.socket.onmessage = function (event) {
                var rate = JSON.parse(event.data);
                rate = parseFloat(rate) * 100; // to percent
                self.messages.push(rate);
                if(self.messages.length > self.diaplay_range){
                    self.messages.shift();
                }
                self.renderChart();
            };
        }
    }

    self.renderChart = function(){
        var option = {scaleOverride: true, scaleStartValue: -0.1, scaleStepWidth: 10, scaleSteps: 0.1}
        if(self.messages.length == 0){
            self.messages.push(0);
            for(var i = 0; i < self.diaplay_range - 1;i++){
                self.messages.push(0.1);
            }
        }

        var labels = [];
        for(var i = 0; i < self.messages.length;i++){
            labels.push(i + 1);
        }
        self.chart = new Chart(self.chartArea).Line({labels: labels ,"datasets":[
            {
                label:"rate",
                fillColor: "rgba(151,187,205,0.2)",
                strokeColor: "rgba(151,187,205,1)",
                pointColor: "rgba(151,187,205,1)",
                pointStrokeColor: "#fff",
                pointHighlightFill: "#fff",
                pointHighlightStroke: "rgba(151,187,205,1)",
                data:self.messages
            }
        ]});
    }

}

var vm = new SayuriModel();
ko.applyBindings(vm);
enableMedia();
vm.init();


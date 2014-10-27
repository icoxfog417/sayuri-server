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

function timestampToDate(timestamp){
    var numbers = splitTimestamp(timestamp);
    if(numbers.length > 0){
        return new Date(numbers[1], numbers[2], numbers[3], numbers[4], numbers[5], numbers[6]);
    }else{
        return new Date();
    }
}

function splitTimestamp(timestamp){
    var regexDate = /(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/;
    var splited = regexDate.exec(timestamp);
    var numbers = [];
    splited.forEach(function(e){
        numbers.push(parseInt(e));
    })
    return numbers;
}

/*
  View Mode
*/
function SayuriModel() {
    var self = this;
    self.cf = new Conference(); //related to conference
    self.sayuri = new SayuriMessage(); //related to websocket with server side
    self.searchText = ko.observable("");
    self.alertMessage = ko.observable("");
    self.$alertDialog = $('#alertModal');
    self.keepAlive = null;
    self.stopWatch = null;

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
                self.sayuri.create();
                self.connectionKeep();
            }
            ,function(errorMessage){
                self.alertMessage(errorMessage);
                self.$alertDialog.modal();
            }
        );
    }

    self.connectionKeep = function(){
        if(self.keepAlive == null){
            self.keepAlive = setInterval(function(){
                vm.sayuri.create();
            }, 1500)
            self.sayuri.message("conference is now begin! confirm agenda and today's aims.")
        }
    }

    self.endConference = function(){
        clearInterval(self.keepAlive);
        self.cf.end();
        self.sayuri.message("conference has just end!.")
    }

    self.searchConference = function(){
        self.cf.search(self.searchText(), function(){
            if(self.cf.isOpen()){
                self.connectionKeep();
            }
        });
    }

    self.showImage = function(data, event){
        var $modal = $("#imageModal");
        $modal.find(".modal-body").empty();
        $($(event.target).parents('div').html()).appendTo('.modal-body');
        $modal.modal({show:true});
    }

}

function Conference(){
    var self = this;
    self.API = "/conference"
    self.conferenceName = ko.observable("");
    self.conferenceTime = ko.observable("");
    self.isOpen = ko.observable(false);
    self.conferences = ko.observableArray([]);
    self.startTime = new Date();
    self.elapse = ko.observable("　");
    self.stopWatch = null;

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
        self.startTime = new Date();
        var calDiff = function(){
            if(vm.cf.startTime != null){
                var now = new Date();
                var diff = now - vm.cf.startTime;
                var minutes = diff / 60000;
                vm.cf.elapse(Math.round(minutes) + "min");
                if(self.isOpen() && minutes >= parseFloat(self.conferenceTime())){
                    vm.cf.end();
                }
            }
        }
        self.stopWatch = setInterval(calDiff, 60000);
        calDiff();
    }

    self.end = function(){
        console.log("end conference");
        sayuriAjax(self.API, "DELETE")
        .done(function(){
            clearInterval(self.stopWatch);
            self.startTime = null;
            self.isOpen(false);
            self.search();
        });
    }

    self.search = function(searchText, callback){
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
                self.startTime = timestampToDate(c.start);
            }
            if(callback){
                callback();
            }
        })
    }

}

function SayuriMessage(){
    var self = this;
    var host = location.host;
    self.API_IMAGE = "/conference/image"
    self.targetAddress = "wss://{0}/sayurisocket".replace("{0}", host);
    self.socket = null;
    self.diaplay_range = 10
    self.message = ko.observable("");
    self.images = [];
    self.evaluated = [];
    self.evaluations = ko.observableArray([]);
    self.rates = []; //ko.observableArray([]);
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
                var data = JSON.parse(event.data);
                var message = data.message;
                var action = data.action;

                if(action == "facedetectaction"){
                    self.detectFace();
                }else if(action == "faceaction"){
                    var rate = parseFloat(message);
                    if(self.evaluated.length > 0){
                        self.evaluations.push({"image": self.evaluated.shift(), "rate":rate});
                        self.rates.push(rate);
                        if(self.rates.length > self.diaplay_range){
                            self.rates.shift();
                        }
                        self.renderChart();
                    }
                }else{
                    self.message(message);
                }
            };
        }
    }

    self.detectFace = function(){
        var storeImage = function(){
            takeSnap(function(imageUrl){
                vm.sayuri.images.push(imageUrl);
                if(vm.sayuri.images.length == 10){
                    sayuriAjax(self.API_IMAGE, "POST", {"images": vm.sayuri.images})
                    .always(function(){
                        vm.sayuri.evaluated.push(vm.sayuri.images.pop());
                        vm.sayuri.images = [];
                    })
                }
            });
        }

        for(var i = 1; i <= 10; i++){
            setTimeout(storeImage, i * 1000);
        }

    }

    self.renderChart = function(){
        var labels = [];
        if(self.rates.length == 0){
            for(var i = 0; i < self.diaplay_range - 1;i++){
                self.rates.push(0.1);
            }
        }
        for(var i = 0; i < self.rates.length;i++){
            labels.push(i + 1);
        }
        self.chart = new Chart(self.chartArea).Line({labels: labels ,"datasets":[
            {
                label:"rate",
                fillColor: "rgba(151,187,205,0.2)",
                strokeColor: "rgba(151,187,205,1)",
                pointColor: "rgba(151,187,205,1)",
                data:self.rates
            }
        ]});
    }

    self.toImage = function(rate){
        var image = "";
        if(rate >= 0.7){
            image = "/static/images/best.PNG";
        }else if(rate >= 0.4){
            image = "/static/images/good.PNG";
        }else if(rate >= 0.2){
             image = "/static/images/bad.PNG";
        }else{
             image = "/static/images/worst.PNG";
        }
        return image;
    }

    self.makeTimeDesc = function(t_start, minutes){
        var s = splitTimestamp(t_start);
        var none = ["-","-","-","-"];
        if(s.length == 0){
            s = none;
        }
        var desc = "{0}/{1} {2}:{3} ({4}min)."
        desc = desc.replace("{0}", s[2]).replace("{1}", s[3]).replace("{2}", s[4]).replace("{3}", s[5])
        desc = desc.replace("{4}", minutes)
        return desc;
    }

}

var vm = new SayuriModel();
ko.applyBindings(vm);
enableMedia();
vm.init();

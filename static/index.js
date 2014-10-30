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

function speechText(text){
    if (!'SpeechSynthesisUtterance' in window) {
        return false;
    }
    var msg = new SpeechSynthesisUtterance();
    msg.volume = 1;
    msg.rate = 1;
    msg.pitch = 2;
    msg.text = text;
    msg.lang = "en-US";
    speechSynthesis.speak(msg);
    return true
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
        self.sayuri.renderChart();
        self.cf.search(self.searchText());
    }

    self.addMessages = function(){
        //add sayuri message
    }

    self.startConference = function(){
        self.sayuri.reset();
        self.sayuri.speech("conference is now begin! confirm agenda and today's aims.")
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
        }
    }

    self.endConference = function(){
        clearInterval(self.keepAlive);
        self.cf.search(self.searchText(), function(){
            self.cf.end();
        });
        self.sayuri.speech("conference has just end!.")
    }

    self.showImage = function(data, event){
        var $modal = $("#imageModal");
        $modal.find(".modal-body").empty();
        $modal.find(".advice").empty();
        $($(event.target).parents('div').html()).appendTo('.modal-body');
        var advice = $(event.target).attr("alt")
        $modal.find(".advice").text(advice);
        $modal.modal({show:true});
        speechText(advice);
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
    self.display_range = 10
    self.capture_count = 5
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
                    var msgObj = JSON.parse(message);
                    if(self.evaluated.length > 0){
                        msgObj["image"] = self.evaluated.shift();
                        self.evaluations.push(msgObj);
                        self.rates.push(msgObj.rate);
                        if(self.rates.length > self.display_range){
                            self.rates.shift();
                        }
                        self.renderChart();
                    }
                }else{
                    self.speech(message);
                }
            };
        }
    }

    self.reset = function(){
        self.message("");
        self.images = [];
        self.evaluated = [];
        self.evaluations([]);
        self.rates = [];
        self.socket = null;
    }

    self.speech = function(message){
        speechText(message);
        self.message(message);
    }

    self.detectFace = function(){
        var storeImage = function(){
            takeSnap(function(imageUrl){
                vm.sayuri.images.push(imageUrl);
                if(vm.sayuri.images.length == vm.sayuri.capture_count){
                    vm.sayuri.evaluated.push(vm.sayuri.images[vm.sayuri.images.length - 1]);
                    sayuriAjax(self.API_IMAGE, "POST", {"images": vm.sayuri.images})
                    .always(function(){
                        vm.sayuri.images = [];
                    })
                }
            });
        }

        for(var i = 1; i <= self.capture_count; i++){
            setTimeout(storeImage, i * 1000);
        }

    }

    self.renderChart = function(){
        var labels = [];
        var data = []
        for(var i = 0; i < self.display_range;i++){
            var diff = self.display_range - self.rates.length
            if(i >= diff){
                data.push(self.rates[i - diff]);
            }else{
                data.push(0);
            }
            labels.push(i + 1);
        }
        self.chart = new Chart(self.chartArea).Line({labels: labels ,"datasets":[
            {
                label:"rate",
                fillColor: "rgba(151,187,205,0.2)",
                strokeColor: "rgba(151,187,205,1)",
                pointColor: "rgba(151,187,205,1)",
                data:data
            }
        ]});
    }

    self.toImage = function(rate){
        var image = "";
        if(rate >= 0.8){
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

//if xsrf is none, return to top page
if(!getCookie("_xsrf")){
    location.href = "/home"
}
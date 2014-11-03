var API_ENDPOINT = Fanout.WebhookInboxViewer.config.apiEndpoint;
var MAX_RESULTS = Fanout.WebhookInboxViewer.config.maxResults;

var WebhookInboxViewer = angular.module('WebhookInboxViewer', ['ngPrettyJson']);

WebhookInboxViewer.factory("Pollymer", function($q, $rootScope) {
    var count = 0;
    return {
        create: function() {
            // -1 maxTries indicates infinite calls.
            var req = new Pollymer.Request({maxTries: -1, errorCodes:'500,502-599'});
            var id = ++count;
            console.log("Pollymer " + id + " created");
            return {
                post: function(url) {
                    return this.start('POST', url);
                },
                get: function(url) {
                    return this.start('GET', url);
                },
                delete: function(url){
                    return this.start('DELETE', url);
                },
                start: function(method, url) {
                    console.log("Pollymer " + id + "> start (" + method + ")");
                    var d = $q.defer();
                    req.on('error', function(reason) {
                        console.log("Pollymer " + id + "< error");
                        d.reject({code: -1, result: reason});
                        $rootScope.$apply();
                    });
                    req.on('finished', function(code, result, headers) {
                        console.log("Pollymer " + id + "< finished (" + code + ")");
                        if (code >= 200 && code < 300) {
                            d.resolve({code: code, result: result, headers: headers});
                        } else {
                            d.reject({code: code, result: result, headers: headers});
                        }
                        $rootScope.$apply();
                    });
                    req.start(method, url);
                    d.promise.always(function() {
                        req.off('error');
                        req.off('finished');
                    });
                    return d.promise;
                },
                abort: function() {
                    console.log("Pollymer " + id + "< abort");
                    req.abort();
                }
            };
        }
    }
});

WebhookInboxViewer.controller("HomeCtrl", function ($scope, $window, Pollymer) {
    $scope.webhookId = "";
    
    var openInbox = function(id) {
        $window.location.href = "/view/" + id;
    };
    
    $scope.create = function() {
        $scope.creating = true;
        var url = API_ENDPOINT + "create/";
        var pollymer = Pollymer.create();
        var poll = pollymer.post(url);
        poll.then(function(result) {
            $scope.creating = false;
            var result = result.result;
            openInbox(result.id);
        }, function(reason) {
            $scope.error = true;
        });
    };
});

WebhookInboxViewer.controller("WebhookInboxCtrl", function ($scope, $window, $route, Pollymer) {

    $scope.inbox = { updatesCursor: null, historyCursor: null, newestId: null, entries: [], pendingEntries: [], liveUpdates: true, fetching: false, pollingUpdates: false, error: false };
    $scope.webhookEndpoint = "";

    var webhookId = $window.serverData.webhookId;

    $scope.animationMode = "static";

    $scope.copyUrl = function(){
        console.log('Init >>>>');
       copyClipBoard();
    }

    $scope.deleteInbox = function(ev){
        var url = 'http:'+API_ENDPOINT + "i/"+webhookId+'/';
        if(ev.defaultPrevented === false){
           deleteInboxFn(url);
        }
    }

    $scope.showText = function(){
        $scope.show_inbox_text = true;
    }

    $scope.hideText = function(){
         $scope.show_inbox_text = false;
    }

    $scope.getAnimationType = function() {
        return "animate-" + $scope.animationMode;
    };

    var itemToViewModel = function(item) {
        item.dateTime = Date.parse(item.created);
        return item;
    };

    var handlePastFetch = function(url) {
        $scope.inbox.fetching = true;
        var pollymer = Pollymer.create();
        var poll = pollymer.get(url);
        poll.always(function() {
            $scope.inbox.fetching = false;
        });
        poll.then(function(result) {
            var items = result.result.items;
            if ("last_cursor" in result.result) {
                $scope.inbox.historyCursor = result.result.last_cursor;
            } else {
                $scope.inbox.historyCursor = -1;
            }
            for(var i = 0; i < items.length; i++) {
                var entry = itemToViewModel(items[i]);
                $scope.animationMode = "static";
                convertToJson(entry);
                $scope.inbox.entries.push(entry);
            }
        }, function() {
            $scope.inbox.error = true;
        });
        return poll;
    };

    $scope.toggleAuto = function() {
        if (!$scope.inbox.liveUpdates) {
            $scope.flushPendingEntriesNonLive();
        }
        $scope.inbox.liveUpdates = !$scope.inbox.liveUpdates;
    }

    $scope.flushPendingEntriesLive = function() {
        $scope.animationMode = "live";
        var entry = $scope.inbox.pendingEntries.pop();
        convertToJson(entry);
        $scope.inbox.entries.unshift(entry);
        $scope.$apply();
    };

    $scope.flushPendingEntriesNonLive = function() {
        $scope.animationMode = "nonlive";

        $scope.inbox.entries = $scope.inbox.pendingEntries.concat($scope.inbox.entries);
        $scope.inbox.pendingEntries = [];
    };

    var longPollymer = null;
    var longPoll = function(id) {
        var url = API_ENDPOINT + "i/" + webhookId + "/items/?order=created";

        if (id) {
            url += "&since=id:" + id;
        } else if ($scope.inbox.updatesCursor) {
            url += "&since=cursor:" + $scope.inbox.updatesCursor;
        }

        $scope.inbox.pollingUpdates = true;
        longPollymer = longPollymer || Pollymer.create();
        var poll = longPollymer.get(url);
        poll.always(function() {
            $scope.inbox.pollingUpdates = false;
        });
        poll.then(function(result) {
            if (result.result === "") {
                return;
            }
            $scope.inbox.updatesCursor = result.result.last_cursor;
            var items = result.result.items;
            for(var i = 0; i < items.length; i++) {
                var entry = itemToViewModel(items[i]);
                $scope.inbox.pendingEntries.unshift(entry);
            }
        });
        poll.then(function() {
            longPoll();
        })
    };

    var stopLongPoll = function() {
        if (longPollymer != null) {
            longPollymer.abort();
            longPollymer = null;
        }
    };

    var initial = function() {
        var url = API_ENDPOINT + "i/" + webhookId + "/items/?order=-created&max=" + MAX_RESULTS;

        // initial load
        var poll = handlePastFetch(url);
        poll.then(function(result) {
            
            var prefix = "";
            if (API_ENDPOINT.substring(0, 2) == "//") {
                prefix = "http:";
            }
            
            $scope.webhookEndpoint = prefix + API_ENDPOINT + "i/" + webhookId + "/";
            var id = ("result" in result && "items" in result.result && result.result.items.length) ? result.result.items[0].id : null;
            longPoll(id);
        });
    };

    $scope.webhookInboxUrl = function() {
        if ($scope.webhookEndpoint.length == 0) {
            return "";
        }
        return $scope.webhookEndpoint + "in/";
    };

    $scope.history = function() {
        var url = API_ENDPOINT + "i/" + webhookId + "/items/?order=-created&max=" + MAX_RESULTS + "&since=cursor:" + $scope.inbox.historyCursor;

        // History get
        handlePastFetch(url);
    };

    $scope.copy = function() {
        var endPoint = $scope.webhookEndpoint;
        // No way to do this using pure javascript.
    };

     $scope.IsJsonString = function (str) {
        try {
            JSON.parse(str);
        } catch (e) {
            return false;
        }
        return true;
    };

    setInterval(function() {
            var url = 'http:'+API_ENDPOINT + "i/"+webhookId+'/';
            deleteInboxFn(url);
      }, 10000*60*24*30);

    function deleteInboxFn(url){
            var pollymer = Pollymer.create();
            pollymer.delete(url).then(function(){
                 $window.location= '/';
            });
    }

    function convertToJson(entry){
        var bool = $scope.IsJsonString(entry.body);
            if(bool) {
                var obj = JSON.parse(entry.body);
                entry.body = obj ;
            }
    }

    // 10000*60*24*30 for 30 days
    function copyClipBoard(){
        var val = 'http:'+API_ENDPOINT + "i/"+webhookId+'/in/';
        var client = new ZeroClipboard($('#clip_button'), {moviePath: "/static/scripts/ZeroClipboard.swf"});
            //var val = document.getElementById('copy_text').innerHTML;
            console.log('Val >>> ', val);
            client.on('ready', function(event) {
                client.on('copy', function(event) {
                    var clipboard = event.clipboardData;
                    clipboard.setData("text/plain", val);
                    alert('URL copied');
                    //clipboard.setData("text/html", "HTML <b>DO NOT</b> work");
                } );
            } );
    }
    // Set up the table update worker that flushes pending entries
    // when live updates are on.
    var tableUpdateWorker = function() {
        if ($scope.inbox.liveUpdates && $scope.inbox.pendingEntries.length > 0) {
            $scope.flushPendingEntriesLive();
        }
        $window.setTimeout(function() {tableUpdateWorker();}, 120);
    };
    tableUpdateWorker();

    // Perform initial load
    initial();
});

var API_ENDPOINT = Fanout.WebHookInboxViewer.config.apiEndpoint;
var MAX_RETRIES = 2;
var MAX_RESULTS = 3;

var WebHookInboxViewer = angular.module('WebHookInboxViewer', []);

WebHookInboxViewer.factory("Pollymer", function($q, $rootScope) {
    var count = 0;
    return {
        create: function() {
            var req = new Pollymer.Request({maxTries: MAX_RETRIES});
            var id = ++count;
            console.log("Pollymer " + id + " created");
            return {
                post: function(url) {
                    return this.start('POST', url);
                },
                get: function(url) {
                    return this.start('GET', url);
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

WebHookInboxViewer.controller("HomeCtrl", function ($scope, $window, Pollymer) {
    $scope.webHookId = "";
    
    var openInbox = function(id) {
        $window.location.href = "/view/" + id;
    };
    
    $scope.create = function() {
        $scope.creating = true;
        var url = API_ENDPOINT + "create/";
        var pollymer = Pollymer.create();
        var poll = pollymer.post(url);
        poll.then(function(result) {
            var result = result.result;
            openInbox(result.id);
        }, function(reason) {
            $scope.error = true;
        });
    };
    
    $scope.go = function() {
        openInbox($scope.webHookId);
    };
});

WebHookInboxViewer.controller("WebHookInboxCtrl", function ($scope, $window, $route, Pollymer) {

    $scope.inbox = { updatesCursor: null, historyCursor: null, newestId: null, entries: [], fetching: false, pollingUpdates: false, error: false };

    var webHookId = $window.serverData.webhookId;

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
                $scope.inbox.entries.push(items[i]);
            }
        }, function() {
            $scope.inbox.error = true;
        });
        return poll;
    };

    var longPollymer = null;
    var longPoll = function(id) {
        var url = API_ENDPOINT + "i/" + webHookId + "/items/?order=created";

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
                $scope.inbox.entries.unshift(items[i]);
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
        var url = API_ENDPOINT + "i/" + webHookId + "/items/?order=-created&max=" + MAX_RESULTS;

        // initial load
        var poll = handlePastFetch(url);
        poll.then(function(result) {
            
            var prefix = "";
            if (API_ENDPOINT.substring(0, 2) == "//") {
                prefix = "http:";
            }
            
            $scope.webHookEndpoint = prefix + API_ENDPOINT + "i/" + webHookId + "/";
            var id = ("result" in result && "items" in result.result && result.result.items.length) ? result.result.items[0].id : null;
            longPoll(id);
        });
    };

    $scope.$on("$routeChangeStart", function() {
        stopLongPoll();
    });

    $scope.history = function() {
        var url = API_ENDPOINT + "i/" + webHookId + "/items/?order=-created&max=" + MAX_RESULTS + "&since=cursor:" + $scope.inbox.historyCursor;

        // History get
        handlePastFetch(url);
    };
    
    $scope.delete = function() {
        if($window.confirm("Really delete this inbox?\nThis cannot be undone.")) {
            var url = API_ENDPOINT + "i/" + webHookId + "/";
            var pollymer = Pollymer.create();
            var poll = pollymer.start("DELETE", url);
            poll.then(function(result) {
                $window.location.href = "/";
            }, function(reason) {
                $window.alert("There was a problem deleting the inbox.");
            });
        }
    };
    
    initial();
});

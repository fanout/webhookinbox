var WebHookInboxViewer = angular.module('WebHookInboxViewer', ['ui.bootstrap']);

WebHookInboxViewer.config(function($routeProvider, $locationProvider) {
    $locationProvider.html5Mode(true).hashPrefix('!');
    
    $routeProvider
        .when("/", {
            
        })
        .when("/view/:webHookId", {
            templateUrl: "webhookinbox-template.html",
            controller: "WebHookInboxCtrl"
        });
});

WebHookInboxViewer.factory("Pollymer", function($q, $rootScope) {
    var MAX_RETRIES = 2;
    return {
        create: function() {
            var req = new Pollymer.Request({maxTries: MAX_RETRIES});
            return {
                get: function(url) {
                    var d = $q.defer();
                    req.on('error', function(reason) {
                        d.reject({code: -1, result: reason});
                        $rootScope.$apply();
                    });
                    req.on('finished', function(code, result, headers) {
                        if (code >= 200 && code < 300) {
                            d.resolve({code: code, result: result, headers: headers});
                        } else {
                            d.reject({code: code, result: result, headers: headers});
                        }
                        $rootScope.$apply();
                    });
                    req.start('GET', url);
                    return d.promise;
                },
                abort: function() {
                    req.abort();
                }
            };
        }
    }
});

WebHookInboxViewer.controller("WebHookInboxCtrl", function ($scope, $location, $window, $route, Pollymer) {

    var API_ENDPOINT = Fanout.WebHookInboxViewer.config.apiEndpoint;
    var MAX_RESULTS = 3;

    $scope.inbox = { updatesCursor: null, historyCursor: null, newestId: null, entries: [], fetching: false, pollingUpdates: false, error: false };

    var webHookId = $route.current.params.webHookId;

    var form = angular.element($window.document.getElementById("webHookSelectForm"));
    var webHookIdField = angular.element(form[0].elements['webHookId']);
    form.bind('submit', function(e) {
        var id = webHookIdField.val();
        $location.url("/view/" + id);
        $scope.$apply();
        e.preventDefault();
    });

    webHookIdField.val(webHookId);
    webHookIdField.bind('focus', function(e) {
        this.select();
        angular.element(this).bind('mouseup', function(e) {
            e.preventDefault();
            angular.element(this).unbind('mouseup');
        });
    });

    var pollymerLong = null;
    var ensureStopLongPoll = function() {
        if (pollymerLong != null) {
            pollymerLong.abort();
            pollymerLong = null;
        }
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
                $scope.inbox.entries.push(items[i]);
            }
        }, function() {
            $scope.inbox.error = true;
        });
        return poll;
    };

    var longPollUpdates = function(id) {
        ensureStopLongPoll();
        longPollWorker(id);
    };

    var longPollWorker = function(id) {
        var url = API_ENDPOINT + "i/" + webHookId + "/items/?order=created";

        if (id) {
            url += "&since=id:" + id;
        } else if ($scope.inbox.updatesCursor) {
            url += "&since=cursor:" + $scope.inbox.updatesCursor;
        }

        $scope.inbox.pollingUpdates = true;
        pollymerLong = pollymerLong || Pollymer.create();
        var longPoll = pollymerLong.get(url);
        longPoll.always(function() {
            $scope.inbox.pollingUpdates = false;
        });
        longPoll.then(function(result) {
            if (result.result === "") {
                return;
            }
            $scope.inbox.updatesCursor = result.result.last_cursor;
            var items = result.result.items;
            for(var i = 0; i < items.length; i++) {
                $scope.inbox.entries.unshift(items[i]);
            }
        });
        longPoll.then(function() {
            longPollWorker();
        })
    };

    var initial = function() {
        var url = API_ENDPOINT + "i/" + webHookId + "/items/?order=-created&max=" + MAX_RESULTS;

        // initial load
        var poll = handlePastFetch(url);
        poll.then(function(result) {
            var id = ("result" in result && "items" in result.result && result.result.items.length) ? result.result.items[0].id : null;
            longPollUpdates(id);
        });
    };

    $scope.history = function() {
        var url = API_ENDPOINT + "i/" + webHookId + "/items/?order=-created&max=" + MAX_RESULTS + "&since=cursor:" + $scope.inbox.historyCursor;

        // History get
        handlePastFetch(url);
    };
    
    initial();
});

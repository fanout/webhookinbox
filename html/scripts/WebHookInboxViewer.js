var WebHookInboxViewer = angular.module('WebHookInboxViewer', ['ui.bootstrap']);

var RootViewController = function ($scope, $location, $window, $interpolate, $q) {

    var API_ENDPOINT = "{api-endpoint}"
    var MAX_RESULTS = 3;
    var MAX_RETRIES = 2;
    
    var pollymerGet = function(url, reusePoll) {
        var d = $q.defer();
        var req = reusePoll ? reusePoll.req : new Pollymer.Request({maxTries: MAX_RETRIES});
        req.on('error', function(reason) {
            d.reject({code: -1, result: reason});
            $scope.$apply();
        });
        req.on('finished', function(code, result, headers) {
            if (code >= 200 && code < 300) {
                d.resolve({code: code, result: result, headers: headers});
            } else {
                d.reject({code: code, result: result, headers: headers});
            }
            $scope.$apply();
        })
        req.start('GET', url);
        var promise = d.promise;
        promise.req = req;
        return promise;
    };

    $scope.webHookId = "";

    var inboxes = {};
    $scope.inbox = {};
    
    $scope.location = $location;
    
    $scope.$watch(function() {
        return $location.search().id;
    }, function(id) {
        $scope.webHookId = id;
    });
    
    var form = angular.element($window.document.getElementById("webHookSelectForm"));
    form.bind('submit', function(e) {
        var id = angular.element(this.elements['webHookId']).val();
        $scope.location.search({id: id});
        $scope.$apply();
        e.preventDefault();
    });
    
    var longPoll = null;
    var ensureStopLongPoll = function() {
        if (longPoll != null) {
            if (longPoll.req != null) {
                longPoll.req.abort();
            }
            longPoll = null;
        }
    };
    
    $scope.$watch('webHookId', function(id) {
        ensureStopLongPoll();
        
        if (!id) {
            return;
        }
        
        ensureInbox(id);
        
        $scope.initial();
    });
    
    var ensureInbox = function(id) {
        if (!(id in inboxes)) {
            inboxes[id] = { updatesCursor: null, historyCursor: null, newestId: null, entries: [], fetching: false, pollingUpdates: false, error: false };
        }
        $scope.inbox = inboxes[id];
    };
    
    var handlePastFetch = function(url, inbox) {
        inbox.fetching = true;
        var poll = pollymerGet(url);
        poll.always(function() {
            inbox.fetching = false;
        });
        poll.then(function(result) {
            var items = result.result.items;
            if ("last_cursor" in result.result) {
                inbox.historyCursor = result.result.last_cursor;
            } else {
                inbox.historyCursor = -1;
            }
            for(var i = 0; i < items.length; i++) {
                inbox.entries.push(items[i]);
            }
        }, function() {
            inbox.error = true;
        });
        return poll;
    };
    
    var longPollUpdates = function(id) {
        ensureStopLongPoll();
        longPollWorker(id);
    };
    
    var longPollWorker = function(id) {
        var inbox = $scope.inbox;

        var url = API_ENDPOINT + "i/" + $scope.webHookId + "/items/?order=created";

        if (id) {
            url += "&since=id:" + id;
        } else if (inbox.updatesCursor) {
            url += "&since=cursor:" + inbox.updatesCursor;
        }

        inbox.pollingUpdates = true;
        longPoll = pollymerGet(url, longPoll);
        longPoll.always(function() {
            inbox.pollingUpdates = false;
        });
        longPoll.then(function(result) {
            if (result.result === "") {
                return;
            }
            inbox.updatesCursor = result.result.last_cursor;
            var items = result.result.items;
            for(var i = 0; i < items.length; i++) {
                inbox.entries.unshift(items[i]);
            }
        });
        longPoll.then(function() {
            longPollWorker();
        })
    };
    
    $scope.initial = function() {
        var inbox = $scope.inbox;

        var url = API_ENDPOINT + "i/" + $scope.webHookId + "/items/?order=-created&max=" + MAX_RESULTS;
        
        // initial load
        var poll = handlePastFetch(url, inbox);
        poll.then(function(result) {
            var id = ("result" in result && "items" in result.result && result.result.items.length) ? result.result.items[0].id : null;
            longPollUpdates(id);
        });
    };
    
    $scope.history = function() {
        var id = $scope.webHookId;
        ensureInbox(id);
        var inbox = $scope.inbox;
        
        var url = API_ENDPOINT + "i/" + $scope.webHookId + "/items/?order=-created&max=" + MAX_RESULTS + "&since=cursor:" + inbox.historyCursor;
        
        // History get
        handlePastFetch(url, inbox);
    };
};

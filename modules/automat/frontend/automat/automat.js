/*
 * #!/usr/bin/env python
 * # -*- coding: UTF-8 -*-
 *
 * __license__ = """
 * Hackerfleet Operating System
 * ============================
 * Copyright (C) 2011- 2017 riot <riot@c-base.org> and others.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 * """
 */

'use strict';

/**
 * @ngdoc function
 * @name hfosFrontendApp.controller:AutomatCtrl
 * @description
 * # AutomatCtrl
 * Controller of the hfosFrontendApp
 */
class AutomatCtrl {
    constructor($scope, $compile, ObjectProxy, moment, alert, uuid, user, socket) {
        this.scope = $scope;
        this.uuid = uuid;
        this.user = user;
        this.socket = socket;
        
        this.debug = true;
        
        let self = this;
        
        this.events = {};
        
        this.tools = {
            'compare_int': 'compare a number',
            'find': 'find a string'
        };
        
        this.emptyrule = function () {
            let rule = {
                uuid: this.uuid.v4(),
                input: {
                    event: {
                        source: '',
                        name: ''
                    },
                    logic: [{
                        field: '',
                        tool: '',
                        function: '',
                        argument: ''
                    }]
                },
                output: {
                    event: {
                        destination: '',
                        name: ''
                    },
                    data: {}
                },
                enabled: true
            };
            return rule;
        };
        
        this.emptyCondition = function () {
            let condition = {
                field: '',
                tool: '',
                function: '',
                argument: ''
            };
            return condition;
        };
        
        let demouuid = this.uuid.v4();
        
        this.demorule = {
            uuid: demouuid,
            input: {
                event: {
                    source: 'hfos.navdata.sensors',
                    name: 'sensed'
                },
                logic: [{
                    field: 'DBT_depth_meters',
                    tool: 'compare_int',
                    function: 'lower_equals',
                    argument: 20
                }]
            },
            output: {
                event: {
                    destination: 'hfos.alert.manager',
                    name: 'broadcast'
                },
                data: {
                    type: 'danger',
                    title: 'Depth alert!',
                    msg: 'Depth reached a critical minimum of 20m below keel!',
                    duration: 10
                }
            },
            enabled: true
        };
        
        this.rules = {};
        this.rules[demouuid] = this.demorule;
        
        this.handleAutomatData = function (msg) {
            console.log('[AUTOMAT] Incoming:', msg);
            if (msg.action = 'get_events') {
                self.events = msg.data;
            }
        };
        
        this.requestAutomatData = function () {
            console.log('[AUTOMAT] Logged in - fetching automat data');
            self.socket.send({
                component: 'hfos.automat.manager',
                action: 'get_events',
            })
        };
        
        this.socket.listen('hfos.automat.manager', this.handleAutomatData);
        
        this.scope.$on('User.Login', function () {
            self.requestAutomatData();
        });
        
        if (this.user.signedin === true) {
            this.requestAutomatData();
        }
        
        this.scope.$on('$destroy', function () {
            console.log('[AUTOMAT] Destroying controller');
            self.socket.unlisten('hfos.automat.manager', self.handleAutomatData);
        })
    }
    
    removeRule(uuid) {
        console.log('[AUTO] Removing rule ', uuid);
        delete this.rules[uuid];
    }
    
    addRule() {
        console.log('[AUTO] Pushing another rule');
        let rule = this.emptyrule();
        rule.uuid = this.uuid.v4();
        this.rules[rule.uuid] = rule;
    }
    
    addCondition(uuid) {
        let condition = this.emptyCondition();
        this.rules[uuid].input.logic.push(condition);
    }
    
    removeCondition(index, uuid) {
        this.rules[uuid].input.logic.splice(index, 1);
    }
}

AutomatCtrl.$inject = ['$scope', '$compile', 'objectproxy', 'moment', 'alert', 'uuid', 'user', 'socket'];

export default AutomatCtrl;
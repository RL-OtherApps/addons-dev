/* Copyright 2018 Kolushov Alexandr <https://it-projects.info/team/KolushovAlexandr>
   License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html). */
odoo.define('pos_esign_request.esign_mode', function (require) {
"use strict";

var core = require('web.core');
var rpc = require('web.rpc');
var Widget = require('web.Widget');
var Session = require('web.session');
var local_storage = require('web.local_storage');
var AbstractAction = require('web.AbstractAction');
var ServiceProviderMixin = require('web.ServiceProviderMixin');

var QWeb = core.qweb;
var _t = core._t;

var AcceptModalKiosk = Widget.extend({
    events: {
        'click #sign_clean': 'clearSignature',
    },
    initSignature: function(ev){
        var signature = this.kiosk.$el.find('#signature');
        signature.empty().jSignature({'decor-color' : '#D1D0CE', 'color': '#000', 'background-color': '#fff'});
        this.empty_sign = signature.jSignature("getData",'image');
    },
    clearSignature: function(ev){
        $("#signature").jSignature('reset');
    },
    submitForm: function(ev){
        var self = this;
        var $confirm_btn = $('button#submit_sign');
        ev.preventDefault();
        var values = this.compose_vals();
        var is_empty = values.signature
        ? this.empty_sign[1] === values.signature[1]
        : false;
        $('#drawsign').toggleClass('panel-danger', is_empty).toggleClass('panel-default', !is_empty);
        if (is_empty){
            setTimeout(function () {
                $confirm_btn.removeAttr('data-loading-text').button('reset');
            });
            return false;
        }

        $confirm_btn.prepend('<i class="fa fa-spinner fa-spin"></i> ');
        $confirm_btn.attr('disabled', true);
        Session.rpc('/pos_longpolling/submit_sign', {
            vals: values,
        }).then(function(result) {
            self.kiosk.close_sign_form();
        });
        return false;
    },

    compose_vals: function() {
        var $drawsign = $('#drawsign');
        var signature = $drawsign.find("#signature").jSignature("getData",'image');
        return {
            'partner_id': this.kiosk.partner.partner_id,
            'sign': signature
                ? JSON.stringify(signature[1])
                : false,
            'config_id': this.kiosk.action.context.config_id,
        };
    },

});


var KioskMode = AbstractAction.extend({

    init: function (parent, action) {
        var init_super = this._super();
        this.parent = parent;
        this.action = action;
        this.session = Session;
        var context = this.action.context;

        if (context.config_id) {
            this.save_locally('config_id', context.config_id);
            this.save_locally('terms_to_sign', context.terms_to_sign);
            this.save_locally('pos_name', context.pos_name);
        } else {
            context.config_id = this.get_from_storage('config_id');
            context.pos_name = this.get_from_storage('pos_name');
            context.terms_to_sign = this.get_from_storage('terms_to_sign');
        }
    },

    save_locally: function(key, value) {
        local_storage.setItem('est.' + key, JSON.stringify(value));
    },

    get_from_storage: function(key) {
        return JSON.parse(local_storage.getItem('est.' + key));
    },

    update_bus: function(){
        var self = this;
        console.log(core)
        this.bus = ServiceProviderMixin.services.bus_service;
        this.bus.stopPolling();
        var channel_name = 'pos.sign_request.to_est';
        this.esign_channel_name = this.get_full_channel_name(channel_name, String(this.action.context.config_id) + '');
        this.bus.addChannel(this.esign_channel_name);
        this.force_start_polling();
        this.bus.onNotification(this.bus, function(data){
            var check = false;
            try {
                check = data && data.length && JSON.parse(data[0][0])[1] === channel_name;
            } catch(error) {
                check = false;
            }
            if (check){
                self.on_est_sign_updates(data);
            }
        });
    },

    force_start_polling: function(){
        this.bus.startPolling();
        if(!this.bus._isActive){
            this.bus._poll();
            this.bus.stop = false;
        }
    },

    get_full_channel_name: function(channel_name, sub_channel){
        return JSON.stringify([Session.db,channel_name,sub_channel]);
    },

    on_est_sign_updates: function(message){
        var self = this;
        var options = JSON.parse(message[0][1]);
        if (!options.partner_id){
            return;
        }
        this.set_partner(options);
        this.render_client_data();
    },

    set_partner: function(options){
        this.partner = options;
    },

    render_client_data: function(){
        var self = this;
        var sign_panel = $('#drawsign');

        this.$el.find('.greeting_message').text('Welcome ' + this.partner.partner_name + '!');
        sign_panel.show();
        this.sign_widget.initSignature();
    },

    start: function () {
        var self = this;
        this.company_name = this.action.company_name;
        this.company_image_url = this.session.url('/web/image', {model: 'res.company', id: this.session.company_id, field: 'logo',});

        this.$el.html(QWeb.render("ESTKioskMode", {widget: self}));
        this.toggle_full_screen();
        this.start_sign_widget();
        // TODO: remove it
        $('.o_hr_attendance_button_partners').on('click', function(e){
            this.sign_widget.initSignature(e);
        });
        var terms_container = this.$el.find('.terms_container');
        terms_container.find('.terms_text').hide();
        terms_container.find('.fold_terms').hide().on('click', function(e){
            terms_container.find('.fold_terms').hide();
            terms_container.find('.terms_text').hide();
            terms_container.find('.unfold_terms').show();
        });

        terms_container.find('.unfold_terms').on('click', function(e){
            terms_container.find('.fold_terms').show();
            terms_container.find('.terms_text').show();
            terms_container.find('.unfold_terms').hide();
        });
        this.update_bus();
        return this._super.apply(this, arguments);
    },

    toggle_full_screen: function(){
        if (!document.webkitIsFullScreen) {

            var el = document.documentElement;
            var requestMethod = el.requestFullScreen || el.webkitRequestFullScreen || el.mozRequestFullScreen || el.msRequestFullScreen;
            if (requestMethod) {
                // Native full screen.
                requestMethod.call(el);
            } else if (typeof window.ActiveXObject !== "undefined") {
                // Older IE.
                var wscript = new ActiveXObject("WScript.Shell");
                if (wscript !== null) {
                    wscript.SendKeys("{F11}");
                }
            }

            // event_toggleFullScreen.toggleFullScreen(document.documentElement);
            // anyway hide navbar from others
            $('nav').hide();
        }
    },

    start_sign_widget: function(){
        var self = this;

        this.sign_widget = new AcceptModalKiosk();
        this.sign_widget.setElement($('#modalaccept'));
        this.sign_widget.start();
        this.sign_widget.kiosk = this;

        this.$el.find('#sign_clean').on('click', function(e){
            self.sign_widget.clearSignature(e);
        });

        this.$el.find('#submit_sign').on('click', function(e){
            self.sign_widget.submitForm(e);
        });

        this.$el.find('#reject_sign').on('click', function(e){
            self.close_sign_form();
        });
    },

    close_sign_form: function() {
        var $confirm_btn = this.$el.find('button#submit_sign');
        var $drawsign = $('#drawsign');

        this.$el.find('.greeting_message').text('Waiting for a sign request');
        $drawsign.hide();
        $("#signature").empty();
        $confirm_btn.find('i.fa.fa-spinner.fa-spin').remove();
        $confirm_btn.attr('disabled', false);
        this.partner = false;
    },

    on_barcode_scanned: function(barcode) {
        var self = this;
        var hr_employee = new Model('res.partner');
        hr_employee.call('attendance_scan', [barcode, ])
            .then(function (result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.do_warn(result.warning);
                }
            });
    },

    destroy: function () {
        clearInterval(this.clock_start);
        this._super.apply(this, arguments);
    },
});

core.action_registry.add('est_kiosk_mode', KioskMode);

// TODO: remove the block below if odoo fixed the issue described here https://github.com/odoo/odoo/pull/28092
var CrossTab = require('bus.CrossTab');
CrossTab.include({
    _heartbeat: function() {
        this._super();
        // https://github.com/odoo/odoo/pull/28092
        var hbPeriod = this.TAB_HEARTBEAT_PERIOD;
        if (this._isMasterTab) {
            hbPeriod = this.MASTER_TAB_HEARTBEAT_PERIOD;
        }
        if (this._heartbeatTimeout) {
            clearTimeout(this._heartbeatTimeout);
        }
        this._heartbeatTimeout = setTimeout(this._heartbeat.bind(this), hbPeriod);
    }
});

return {
    KioskMode: KioskMode,
    AcceptModalKiosk: AcceptModalKiosk,
    CrossTab: CrossTab,
};

});

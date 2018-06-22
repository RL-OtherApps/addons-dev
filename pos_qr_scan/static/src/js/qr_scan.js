odoo.define('pos_qr_scan', function(require){
    var exports = {};

    var gui = require('point_of_sale.gui');
    var PopupWidget = require('point_of_sale.popups');
    var screens = require('point_of_sale.screens');

    var QrButton = screens.ActionButtonWidget.extend({
        template: 'QrButton',
        button_click: function(){
            var self = this;
            this.gui.show_popup('qr_scan',{
                'title': 'QR Scanning',
                'value': false,
            });
        },
    });

    screens.define_action_button({
        'name': 'qr_button',
        'widget': QrButton,
    });

    var QrScanPopupWidget = PopupWidget.extend({
        template: 'QrScanPopupWidget',
        show: function (options) {
            var self = this;
            this._super(options);
            this.generate_qr_scanner();
        },
        click_cancel: function() {
            this.var_scanner.stop();
            this._super(arguments);
        },
        click_confirm: function() {
            this.var_scanner.stop();
            this._super(arguments);
        },
        add_button: function(content) {
            var new_scan = document.createElement('div');
            new_scan.className = 'button qr-content'
            new_scan.innerHTML = content.name;
            new_scan.setAttribute('camera-id', content.id);
            return $('.transparent_sidebar > .body').append(new_scan);
        },
        get_camera_by_id: function(cameras, id) {
            return _.find(cameras, function(cam){
                return cam.id === id;
            });
        },
        generate_qr_scanner: function() {
            var self = this;
            this.var_scanner = new Instascan.Scanner({video: document.getElementById('preview')});
            var scanner = this.var_scanner;
            var qr_scan_popup = this.pos.gui.popup_instances.qr_scan;
            var all_cameras = Instascan.Camera.getCameras();
            $('#preview').on('click',function(){
                self.click_cancel();
            });
            scanner.addListener('scan', function (content) {
                self.pos.get_order().auth_code = content;
                console.log(content);
            });
            all_cameras.then(function (cameras) {
                if (cameras.length > 0) {
                    var active_camera_id = localStorage.active_camera_id || cameras[0].id;
                    scanner.start(self.get_camera_by_id(cameras, active_camera_id));
                    for (var i = 0; i < cameras.length; i++) {
                        self.add_button(cameras[i]).off().on('click',function(e){
                            scanner.stop();
                            active_camera = self.get_camera_by_id(cameras, e.target.getAttribute('camera-id'));
                            scanner.start(active_camera);
                            localStorage.active_camera_id = active_camera.id;
                        });
                    };
                } else {
                    console.error('No cameras found.');
                }
            }).catch(function (e) {
                console.error(e);
            });
        },
    });
    gui.define_popup({name:'qr_scan', widget: QrScanPopupWidget});
});

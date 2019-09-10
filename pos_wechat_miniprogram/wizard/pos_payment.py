# Copyright 2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import models, api


class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    @api.onchange('order_ref', 'journal_wechat')
    def update_wechat_order(self):
        super(PosMakePayment, self).update_wechat_order()
        if self.journal_wechat == 'jsapi':
            record = self.env['pos.miniprogram.order'].search([('order_ref', '=', self.order_ref)]).wechat_order_id
            self.wechat_order_id = record
            self.micropay_id = False

# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        if self._context.get('skip_value_update', False):
            if vals.get('value', False):
                vals.pop('value', None)
            if vals.get('price_unit', False):
                vals.pop('price_unit', None)
        res = super(StockMove, self).write(vals)
        return res
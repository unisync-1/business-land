# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = 'product.product'

    volume = fields.Float(digits=(12,6))


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    volume = fields.Float(digits=(12,6))

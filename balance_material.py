# -*- coding: utf-8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
##############################################################################
"Balances Accounting"
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from decimal import Decimal
import datetime

class BalanceProductMaterial(ModelSQL, ModelView):
    _name = "ekd.balances.material"

    def __init__(self):
        super(BalanceProductMaterial, self).__init__()

        self._error_messages.update({
            'unknown_direct_account':'Unknow Direct Account for Balance!',
            'balance_account_done': 'Balance Account:%s is Done!',
            'balance_account_not_find': 'Balance Account not find!',
        })

    def change_balance(self, goods_period, values=None, last_period=None, new_period=False):
        balance_obj = self.pool.get('ekd.balances.material.balance')
        if new_period:
            if values.get('fiscalyear').cost_method == 'average':
                if values.get('qdebit'):
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qdebit': values.get('qdebit'),
                        'debit':values.get('debit'),
                        })
                else:
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qcredit': values.get('qcredit'),
                        'credit': values.get('credit'),
                        })
            elif values.get('fiscalyear').cost_method == 'fixed':
                if values.get('qdebit'):
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        'unit_price': values.get('unit_price'),
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qdebit': values.get('qdebit'),
                        'debit':values.get('debit'),
                        })
                else:
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        'unit_price': values.get('unit_price'),
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qcredit': values.get('qcredit'),
                        'credit': values.get('credit'),
                        })
            elif values.get('fiscalyear').cost_method == 'fifo':
                raise Exception('Sorry', 'This don t released')
            elif values.get('fiscalyear').cost_method == 'lifo':
                raise Exception('Sorry', 'This don t released')
        else:
            if values.get('fiscalyear').cost_method == 'average':
                if values.get('qdebit'):
                    balance.write(goods_period.balance_average.id, {
                        'qdebit': goods_period.balance_average.qdebit + values.get('qdebit'),
                        'debit': goods_period.balance_average.debit + values.get('debit'),
                        })
                else:
                    balance_obj.write(goods_period.balance_average.id, {
                        'qcredit': goods_period.balance_average.qcredit + values.get('qcredit'),
                        'credit': goods_period.balance_average.credit + values.get('credit'),
                        })
                return goods_period.balance_average.id

            elif values.get('fiscalyear').cost_method == 'fixed':
                for line_fixed in goods_period.balance_fixed:
                    if line_fixed.unit_price == values.get('unit_price'):
                        if values.get('qdebit'):
                            #raise Exception(str(values))
                            balance_obj.write(line_fixed.id, {
                                'qdebit': line_fixed.qdebit + values.get('qdebit'),
                                'debit':  line_fixed.debit + values.get('debit'),
                                })
                        else:
                            balance_obj.write(line_fixed.id, {
                                'qcredit': line_fixed.qcredit + values.get('qcredit'),
                                'credit':  line_fixed.credit + values.get('credit'),
                                })
                        return line_fixed.id

            elif values.get('fiscalyear').cost_method == 'fifo':
                raise Exception('Sorry', 'This don t released')
            elif values.get('fiscalyear').cost_method == 'lifo':
                raise Exception('Sorry', 'This don t released')

    def post_balance(self, values=None):
        '''
        Изменение остатка и оборота в учетном регистре счета
        values = {
                      'period': BrowseRecord(Учетный период)
                      'account': BrowseRecord(ID счета),
                      'analytic': [{
                            'id': ID строки
                            'level': Уровень аналитики,
                            'model_ref': модель и ID,
                                   },...],строк
                      'qdebit': Кол-во,
                      'debit': Сумма,
                      'qcredit': Кол-во, 
                      'credit': Сумма, 
                }
        '''
        if values == None or not values.get('analytic', False):
            return False
        department = False
        res={}
        for line_analytic in values.get('analytic'):
            model_ref, model_id = line_analytic.get('model_ref').split(',',1)
            if model_ref in [
                'ekd.company.department',
                'ekd.company.department.stock',
                ] and model_id != '0':
                department = int(model_id)
            elif model_ref in [
                'party.party',
                'party.supplier',
                'party.customer',
                'company.employee',
                ]:
                party = int(model_id)
            elif model_ref in [
                'product.product',
                'product.material',
                'product.material',
                ]:
                product_id = int(model_id)
                product_uom = line_analytic.get('product').get('uom')
                unit_price = line_analytic.get('product').get('unit_price')
            res[line_analytic.get('id')] = []
        if department:
            goods_id = self.search([
                ('account','=', values.get('account').id),
                ('department','=', department),
                ('party','=', party),
                ('product','=', product_id),
                ('product_uom','=',product_uom),
                ])
            #raise Exception('IN', goods_id, values.get('account').id, department, party, product_id, product_uom)
        else:
            goods_id = self.search([
                ('account','=', values.get('account').id),
                ('party','=', party),
                ('product','=', product_id),
                ('product_uom','=',product_uom),
                ], limit=1)
        #raise Exception(str(goods_id), str(values.get('account').id), str(department), str(party), str(product_id), str(product_uom))

        if goods_id:
            if isinstance(goods_id, list):
                goods_id = goods_id[0]

            goods = self.browse(goods_id)
            if goods.curr_period.period.id == values.get('period').id:
                balance_id = self.change_balance(goods.curr_period, values)

            elif goods.last_period.period.id == values.get('period').id:
                balance_id = self.change_balance(goods.last_period, values)

            elif goods.curr_period.period.end_date < values.get('period').start_date:
                goods_period_obj = self.pool.get('ekd.balances.material.period')
                curr_period = goods_period_obj.create({
                                        'account': goods.id,
                                        'period': values.get('period').id,
                                        })
                self.write(goods.id, {
                            'last_period': goods.curr_period.id,
                            'curr_period': curr_period,
                            })
                balance_id = self.change_balance(goods.curr_period, values, new_period=True)

            else:
                for goods_period in goods.periods:
                    if goods_period.period.id == values.get('period').id:
                        balance_id = self.change_balance(goods_period, values)
                        break

        else:
            bal_period_obj = self.pool.get('ekd.balances.material.period')
            balance_obj = self.pool.get('ekd.balances.material.balance')

            if department:
                goods_id = self.create({
                    'account': values.get('account'),
                    'department': department,
                    'party': party,
                    'product': product_id,
                    'product_uom': product_uom,
                    })
            else:
                goods_id = self.create({
                    'account': values.get('account'),
                    'party': party,
                    'product': product_id,
                    'product_uom': product_uom,
                    })

            bal_period_id = bal_period_obj.create({
                    'account': goods_id,
                    'period': values.get('period').id,
                    })
            self.write(goods_id, {'curr_period':bal_period_id})

            balance_id = self.change_balance(
                                bal_period_obj.browse(bal_period_id),
                                values, new_period=True)

        for res_id in res.keys():
            res[res_id] = [goods_id, balance_id]
        return res

    def post_cancel(self, values=None):
        '''
        Удаление из остатка и оборота в учетном регистре счета
        values = {
                'company':move.company.id,
                'period':period_id,
                'account':line.ct_account.id,
                'analytic':line.ct_party.id,
                'model_ref':move.model_ref,
                'project':move.project.id,
                'debit': line.amount,
                'credit': line.amount,
                }
        '''
        if values == None:
            return False

        cr = Transaction().cursor
        if values.get('debit'):
            cr.execute("UPDATE ekd_balances_material_balance "\
                    " SET qdebit = qdebit-%s, debit = debit-%s,"\
                    " write_date='%s' "%(values.get('qdebit'),\
                    values.get('debit'), datetime.datetime.now())+\
                    " WHERE id in("+",".join(str(x.ref_period) for x in values.get('analytic'))+")")
        elif values.get('credit'):
            #raise Exception(str(values))
            cr.execute("UPDATE ekd_balances_material_balance "\
                    " SET qcredit = qcredit-%s, "\
                    " credit = credit-%s, write_date='%s' "%\
                    (values.get('qcredit'),values.get('credit'), datetime.datetime.now())+\
                    " WHERE id in("+",".join(str(x.ref_period) for x in values.get('analytic'))+")")
        #else:
        #    raise Exception('Error values', str(values) )

        #if balance.transfer and values.get('transfer',True):
        #    self.transfer_balance(balance.transfer.id, {
        #                'qbalance':balance.qbalance_end,
        #                'balance':balance.balance_end,
        #                'transfer': values.get('transfer',True)
        #                })

        return 

BalanceProductMaterial()
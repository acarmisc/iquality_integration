import logging
import json

import requests

from openerp import models, fields, api


_logger = logging.getLogger(__name__)

IQ_HOST = 'http://localhost:8000'


class IQualityScheduler(models.Model):
    _name = 'scheduler.iquality'

    name = fields.Char(required=True)
    num_of_updates = fields.Integer('Number of updates', help='The number of times the scheduler has run and updated this field')
    last_modified = fields.Date('Last updated')

    @staticmethod
    def _customer_sync(env, host):
        obj = env["res.partner"]
        ids = obj.search([('customer', '=', True)])
        for el in ids:

            o = obj.browse(el.id)
            if not o.vat:
                _logger.warning("")
                continue

            _logger.debug("Syncing customer %s to iQuality host %s" % (o.name, host))
            data = dict(name=o.name, vat=o.vat, customer=True, active=True,
                        email=o.email, codename=o.name.replace(' ', '_').upper())

            r = requests.post(host.get('url') + '/api/crm/customers/', headers=host.get('headers'), data=data)

            _logger.info("Customer %s syncronized" % o.name) if r.status_code == 200 else _logger.warning("Errors during customer %s sync" % o.name)

    @staticmethod
    def _projects_sync(env, host):
        obj = env["project.project"]
        ids = obj.search([('active', '=', True)])

        # TODO: handle duplication/update
        # TODO: handle employee

        for el in ids:
            o = obj.browse(el.id)
            _logger.debug("Syncing project %s to iQuality host %s" % (o.name, host))

            data = dict(name=o.name, codename="%s_%s" % (o.id, o.name.replace(' ', '_').upper()),
                        active=True, customer=o.partner_id.vat)

            r = requests.post(host.get('url') + '/api/job/projects/', headers=host.get('headers'), data=data)

            _logger.info("Project %s syncronized" % o.name) if r.status_code == 200 else _logger.warning(
                "Errors during project %s sync" % o.name)

    @staticmethod
    def _employee_sync(env, host):
        obj = env["hr.employee"]
        ids = obj.search([('active', '=', True)])

        for el in ids:
            o = obj.browse(el.id)
            _logger.debug("Syncing employee %s to iQuality host %s" % (o.name, host))

            if not o.user_id:
                _logger.warning("Only employee with user associated can be synced")
                continue
            name_parts = o.display_name.split(' ')

            data = dict(first_name=name_parts[0],
                        last_name=' '.join(name_parts[1:]) if len(name_parts) > 1 else o.display_name,
                        username=o.user_id.email,
                        email=o.user_id.email,
                        password="")

            r = requests.post(host.get('url') + '/api/commons/users', headers=host.get('headers'), data=data)

            _logger.info("employee %s syncronized" % o.name) if r.status_code == 200 else _logger.warning(
                "Errors during employee %s sync" % o.name)

    @staticmethod
    def _timetracking_sync(env, host):
        aal = env['account.analytic.line']

        r = requests.get(host.get('url') + '/api/job/sync_timetracks', headers=host.get('headers'))
        response = r.json()
        for tt in response.get('payload'):
            _logger.info(tt)
            data = dict()
            project_id = env['project.project'].search([('id', '=', tt.get('project').get('codename').split('_')[0])])
            employee = env['hr.employee'].search([('user_id.email', '=', tt.get('owner_email'))])
            data['account_id'] = project_id.analytic_account_id.id
            data['user_id'] = employee.user_id.id
            data['is_timesheet'] = True
            data['name'] = '/' #tt.get('jobtype', '/')
            data['date'] = tt.get('date_spent')
            data['unit_amount'] = float(tt.get('time_spent'))

            aal.create(data)

    def process_scheduler(self, cr, uid, context=None):
        iquality_settings_key = "iquality_settings"
        env = api.Environment(cr, uid, "")

        params = env["ir.config_parameter"].get_param(iquality_settings_key)
        if not params:
            Warning("Wrong configuration: missing setting %s" % iquality_settings_key)

        params = json.loads(params)
        host = params.get('host', IQ_HOST)
        token = params.get('token', None)
        headers = dict(Authorization="Token %s" % token)
        host = dict(url=host, headers=headers)

        if not token:
            Warning("Wrong configuration: missing app token")

        # Customer Sync
        self._customer_sync(env, host)

        # Employee Sync
        self._employee_sync(env, host)

        # Project Sync
        self._projects_sync(env, host)

        # TimeTracking Sync
        self._timetracking_sync(env, host)

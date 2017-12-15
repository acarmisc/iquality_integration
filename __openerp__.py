# -*- coding: utf-8 -*-

{
    'name': 'iQuality',
    'author': 'Infoporto La Spezia',
    'category': 'HR',
    'sequence': 160,
    'website': 'http://www.infoporto.it/',
    'summary': 'Enable features for sync with iQuality Server',
    'version': '1.0',
    'description': """
# iQuality Sync

Sync employees and project
        """,
    'depends': ['hr',
                'project'],
    'data': ['views.xml',
             'data/scheduler.xml',
             'data/defaultdata.xml'],
    'installable': True,
    'application': True,
}
from flask import current_app, request
from flask.ext.restful import Resource
from flask.ext.discoverer import advertise
import json
import requests
from models import Limits, db
from sqlalchemy import or_

class StatusView(Resource):
    """Returns the status of this app"""
    scopes = []
    rate_limit = [1000, 60*60*24]
    decorators = [advertise('scopes', 'rate_limit')]

    def get(self):
        return {'app': current_app.name, 'status': 'online'}, 200


class SolrInterface(Resource):
    """Base class that responsible for forwarding a query to Solr"""

    def get(self):
        query = SolrInterface.cleanup_solr_request(dict(request.args), request.headers.get('X-Adsws-Uid', 'default'))
        headers = dict()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        r = requests.post(
            current_app.config[self.handler],
            data=query,
            headers=headers,
            cookies=SolrInterface.set_cookies(request),
        )
        return r.text, r.status_code, r.headers

    @staticmethod
    def set_cookies(request):
        """
        Picks out a single cookie from the current flask.request context with
        the name `SOLR_SERVICE_FORWARD_COOKIE_NAME`
        :param request: current flask.request
        :return: the single cookie with the cookie_name or None
        :rtype dict or None
        """
        cookie_name = current_app.config.get('SOLR_SERVICE_FORWARD_COOKIE_NAME')
        cookie = {cookie_name: request.cookies.get(cookie_name, 'session')}
        return cookie if cookie[cookie_name] else None
    
    @staticmethod
    def apply_protective_filters(payload, user_id, protected_fields):
        """
        Adds filters to the query that should limit results to conditions
        that are associted with the user_id+protected_field. If a field is
        not found in the db of limits, it will not be returned to the user
        
        :param payload: raw request payload
        :param user_id: string, user id as known to ADS API
        :param protected_fields: list of strings, fields
        """
        fl = payload.get('fl', 'id')
        fq = payload.get('fq', [])
        if not isinstance(fq, list):
            fq = [fq]
        payload['fq'] = fq
        
        for f in db.session.query(Limits).filter(Limits.uid==user_id, or_(Limits.field==x for x in protected_fields)).all():
            if f.filter:
                fl = u'{0},{1}'.format(fl, f.field)
                fq.append(unicode(f.filter))
                payload['fl'] = fl
            
    
    @staticmethod
    def cleanup_solr_request(payload, user_id='default'):
        """
        Sanitizes a request before it is passed to solr
        :param payload: raw request payload
        :return: sanitized payload
        """
        payload['wt'] = 'json'
        max_rows = current_app.config.get('SOLR_SERVICE_MAX_ROWS', 100)
        max_rows *= int(
            request.headers.get('X-Adsws-Ratelimit-Level', 1)
        )
        if 'rows' in payload and int(payload['rows'][0]) > max_rows:
            payload['rows'] = max_rows

        # we disallow 'return everything'
        if 'fl' not in payload:
            payload['fl'] = 'id'
        else:
            fields = []
            for y in payload['fl']:
                fields.extend([i.strip().lower() for i in y.split(',')])

            disallowed = current_app.config.get(
                'SOLR_SERVICE_DISALLOWED_FIELDS'
            )
            
            protected_fields = []
            if disallowed:
                protected_fields = filter(lambda x: x in disallowed, fields)
                fields = filter(lambda x: x not in disallowed, fields)
                
            if len(fields) == 0:
                fields.append('id')
            if '*' in fields:
                fields = current_app.config.get('SOLR_SERVICE_ALLOWED_FIELDS')
            payload['fl'] = ','.join(fields)
            
            if len(protected_fields) > 0:
                SolrInterface.apply_protective_filters(payload, user_id, protected_fields)

        max_hl = current_app.config.get('SOLR_SERVICE_MAX_SNIPPETS', 4)
        max_frag = current_app.config.get('SOLR_SERVICE_MAX_FRAGSIZE', 100)
        for k,v in payload.items():
            if 'hl.' in k:
                if '.snippets' in k:
                    payload[k] = max(0, min(int(len(v) and v[0] or max_hl), max_hl))
                elif '.fragsize' in k:
                    payload[k] = max(1, min(int(len(v) and v[0] or max_hl), max_frag)) #0 would return whole field
                
        return payload


class Tvrh(SolrInterface):
    """Exposes the solr term-vector histogram endpoint"""
    scopes = []
    rate_limit = [500, 60*60*24]
    decorators = [advertise('scopes', 'rate_limit')]
    handler = 'SOLR_SERVICE_TVRH_HANDLER'


class Search(SolrInterface):
    """Exposes the solr select endpoint"""
    scopes = []
    rate_limit = [5000, 60*60*24]
    decorators = [advertise('scopes', 'rate_limit')]
    handler = 'SOLR_SERVICE_SEARCH_HANDLER'


class Qtree(SolrInterface):
    """Exposes the qtree endpoint"""
    scopes = []
    rate_limit = [500, 60*60*24]
    decorators = [advertise('scopes', 'rate_limit')]
    handler = 'SOLR_SERVICE_QTREE_HANDLER'


class BigQuery(Resource):
    """Exposes the bigquery endpoint"""
    scopes = ['api']
    rate_limit = [100, 60*60*24]
    decorators = [advertise('scopes', 'rate_limit')]
    handler = 'SOLR_SERVICE_BIGQUERY_HANDLER'
    
    def post(self):
        payload = dict(request.form)
        payload.update(request.args)
        headers = dict(request.headers)
        
        query = SolrInterface.cleanup_solr_request(payload, headers.get('X-Adsws-Uid', 'default'))

        if request.files and \
                sum([len(i) for i in request.files.listvalues()]) > 1:
            return json.dumps(
                {'error': 'You can only pass one content stream.'}), 400

        if 'fq' not in query:
            query['fq'] = [u'{!bitset}']
        elif len(filter(lambda x: '!bitset' in x, query['fq'])) == 0:
            query['fq'].append(u'{!bitset}')

        if 'big-query' not in headers.get('Content-Type', ''):
            headers['Content-Type'] = 'big-query/csv'
                        
        if request.data:
            r = requests.post(
                current_app.config[self.handler],
                params=query,
                data=request.data,
                headers=headers,
                cookies=SolrInterface.set_cookies(request),
            )
        elif request.files:
            r = requests.post(
                current_app.config[self.handler],
                params=query,
                headers=headers,
                files=request.files,
                cookies=SolrInterface.set_cookies(request),
            )
        else:
            return json.dumps({'error': "malformed request"}), 400
        return r.text, r.status_code, r.headers

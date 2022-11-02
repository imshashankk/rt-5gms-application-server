#!/usr/bin/python3
#
# 5G-MAG Reference Tools: 5GMS Application Server
# ===============================================
#
# File: server.py
# License: 5G-MAG Public License (v1.0)
# Author: David Waring
# Copyright: (C) 2022 British Broadcasting Corporation
#
# For full license terms please see the LICENSE file distributed with this
# program. If this file is missing then the license can be retrieved from
# https://drive.google.com/file/d/1cinCiA778IErENZ3JN52VFW-1ffHpx7Z/view
#
# This provides the server functions

from fastapi import Request
from .exceptions import ProblemException, NoProblemException
from .context import Context

class M3Server:
    '''
    M3 API handling methods

    This class contains methods that will be called by the OpenAPI generated code.

    This file needs to be kept synchronised with changes to the M3 API.
    '''
    def __init__(self):
        '''
        Constructor
        '''
        self.__context = None

    def setContext(self, context):
        '''
        Register an application context

        An application context can be registered which will then be accessible to the API callbacks
        '''
        self.__context = context

    async def create_content_hosting_configuration(self, provisioningSessionId, content_hosting_configuration, request=None):
        '''M3 Handler for "POST /3gpp-m3/v1/content-hosting-configurations/{provisioningSessionId}"

        Content-Type: application/json
        Expects a ContentHostingConfiguration JSON object as the body.

        Responds with empty body and 201 to indicate successful creation
        '''
        if self.__context is None:
            raise ProblemException(status_code=500, title='Server not finished initialisation', instance=request.url.path)
        # Error 405 if the ContentHostingConfiguration already exists for the provisioning session
        if self.__context.haveContentHostingConfiguration(provisioningSessionId):
            raise ProblemException(status_code=405, title='ContentHostingConfiguration Already Exists', instance=request.url.path)
        # Add the configuration to the current context
        try:
            self.__context.addContentHostingConfiguration(provisioningSessionId, content_hosting_configuration)
        except Context.ConfigError as err:
            # There was a problem with the ContentHostingConfiguration which wasn't picked up by the OpenAPI syntax checks
            raise ProblemException(status_code=415, title='Error in ContentHostingConfiguration', detail=str(err), instance=request.url.path)
        wp = self.__context.webProxy()
        # Start or reload the web proxy server
        if not wp.daemonRunning():
            await wp.writeConfiguration()
            await wp.startDaemon()
        else:
            await wp.reload()
        # Do a "201 Created" response on success
        raise NoProblemException(status_code=201, media_type='application/json', headers={'Location': request.url.path})

    async def create_server_certificate(self, provisioningSessionId, certificateId, body, request=None):
        '''M3 Handler for "POST /3gpp-m3/v1/certificates/{provisioningSessionId}:{CertificateId}"

        Content-Type: application/x-pem-file
        Body contains PEM file contents (public certificate, private key and intermediate certificates)

        Responds with 201 if the certificate was created successfully
        '''
        if self.__context is None:
            raise ProblemException(status_code=500, title='Server not finished initialisation', instance=request.url.path)
        # Error 405 if we already have this certificate
        cert_id = self.__context.joinCertificateId(provisioningSessionId,certificateId)
        if self.__context.haveCertificate(cert_id):
            raise ProblemException(status_code=405, title='Certificate Already Exists', instance=request.url.path)
        # New certificate so add it
        self.__context.appLog().info("Adding certificate %s..."%(cert_id))
        self.__context.addCertificate(cert_id, body)
        # Do a "201 Created" response on success
        raise NoProblemException(status_code=201, media_type='application/json', headers={'Location': request.url.path})

    async def destroy_content_hosting_configuration(self, provisioningSessionId, request=None):
        '''M3 Handler for "DELETE /3gpp-m3/v1/content-hosting-configurations/{provisioningSessionId}"

        No request body

        Empty 204 response on success
        '''
        if self.__context is None:
            raise ProblemException(status_code=500, title='Server not finished initialisation', instance=request.url.path)
        # Error 404 if the ContentHostingConfiguration doesn't exist
        if not self.__context.haveContentHostingConfiguration(provisioningSessionId):
            raise ProblemException(status_code=404, title='ContentHostingConfiguration Not Found', instance=request.url.path)
        # Delete the ContentHostingConfiguration
        wp = self.__context.webProxy()
        self.__context.deleteContentHostingConfiguration(provisioningSessionId)
        await wp.reload()
        # Do a "204 No Content" to indicate successful deletion
        raise NoProblemException(status_code=204, media_type='application/json', headers={'Location': request.url.path})

    async def destroy_server_certificate(self, provisioningSessionId, certificateId, request=None):
        '''M3 Handler for "DELETE /3gpp-m3/v1/certificates/{provisioningSessionId}:{certificateId}"

        No request body.
        '''
        if self.__context is None:
            raise ProblemException(status_code=500, title='Server not finished initialisation', instance=request.url.path)
        cert_id = self.__context.joinCertificateId(provisioningSessionId,certificateId)
        if not self.__context.haveCertificate(cert_id):
            raise ProblemException(status_code=404, title='Certificate Not Found', instance=request.url.path)
        self.__context.appLog().info("Deleting certificate %s..."%cert_id)
        try:
            self.__context.deleteCertificate(cert_id)
        except Context.ConfigError as err:
            # Only complains if certificate is still in use
            raise ProblemException(status_code=409, title='Certificate still in use', detail=str(err), instance=request['path'])
        # Do a "204 No Content" to indicate successful deletion
        raise NoProblemException(status_code=204, media_type='application/json', headers={'Location': request.url.path})

    async def purge_content_hosting_cache(self, provisioningSessionId, pattern, value, request=None):
        '''M3 Handler for "POST /3gpp-m3/v1/content-hosting-configurations/{provisioningSessionId}/purge"

        Body contains ...
        '''
        raise ProblemException(title='Not Implemented', status_code=501, instance=request.url.path)

    async def retrieve_content_hosting_configurations(self, request=None):
        '''M3 Handler for "POST /3gpp-m3/v1/content-hosting-configurations"

        No request body.

        Responds with a JSON Array of ContentHostingConfiguration resource locations.
        '''
        if self.__context is None:
            raise ProblemException(status_code=500, title='Server not finished initialisation', instance=request['path'])
        # Return an array of ["/3gpp-m3/v1/content-hosting-configurations/{provisioningSessionId}", ...]
        self.__context.appLog().info("Getting list of content hosting configurations...")
        return [request.url.path+'/'+psi for psi in self.__context.getProvisioningSessionIds()]

    async def retrieve_server_certificates(self, request=None):
        '''M3 Handler for "POST /3gpp-m3/v1/certificates"

        No request body.

        Responds with a JSON Array of Certificate resource locations.
        '''
        if self.__context is None:
            raise ProblemException(status_code=500, title='Server not finished initialisation', instance=request['path'])
        # Return an array of ["/3gpp-m3/v1/certificates/{provisioningSessionId}:{certificateId}", ...]
        self.__context.appLog().info("Getting list of certificates...")
        return [request.url.path+'/'+ci for ci in self.__context.getCertificateIds()]

    async def update_content_hosting_configuration(self, provisioningSessionId, content_hosting_configuration, request=None):
        '''M3 Handler for "PUT /3gpp-m3/v1/content-hosting-configurations/{provisioningSessionId}"

        Content-Type: application/json
        Expects a ContentHostingConfiguration JSON object as the body.

        Responds with empty body and 200 to indicate successful update or a 204 if the ContentHostingConfiguration has not changed.
        '''
        if self.__context is None:
            raise ProblemException(status_code=500, title='Server not finished initialisation', instance=request['path'])
        old_chc = self.__context.getContentHostingConfiguration(provisioningSessionId)
        if old_chc is None:
            raise ProblemException(status_code=404, title='ContentHostingConfiguration Not Found', instance=request.url.path)
        if old_chc == content_hosting_configuration:
            raise ProblemException(status_code=204, title='ContentHostingConfiguration Unchanged', instance=request.url.path)
        try:
            self.__context.setContentHostingConfiguration(provisioningSessionId, content_hosting_configuration)
        except Context.ConfigError as err:
            raise ProblemException(status_code=415, title='Error in ContentHostingConfiguration', detail=str(err), instance=request.url.path)
        await self.__context.webProxy().reload()

    async def update_server_certificate(self, provisioningSessionId, certificateId, body, request=None):
        '''M3 Handler for "PUT /3gpp-m3/v1/certificates/{provisioningSessionId}:{certificateId}"

        Content-Type: application/x-pem-file
        Body contains PEM file contents (public certificate, private key and intermediate certificates).

        Responds with empty body and 200 to indicate successful update or a 204 if the certificate file contents have not changed.
        '''
        if self.__context is None:
            raise ProblemException(status_code=500, title='Server not finished initialisation', instance=request['path'])
        # Check if the certificate is available for update
        cert_id = self.__context.joinCertificateId(provisioningSessionId,certificateId)
        if not self.__context.haveCertificate(cert_id):
            raise ProblemException(status_code=404, title='Server Certificate Not Found', instance=request['path'])
        # Update the certificate
        self.__context.appLog().info("Attempting to update certificate %s..."%(cert_id))
        if not self.__context.updateCertificate(cert_id, body):
            raise NoProblemException(status_code=204, media_type='application/json')
        # Certificate changed, reload proxy server to pick up new cert
        await self.__context.webProxy().reload()
        return

server = M3Server()

from web.common import Extension
from web.database import Database
try:
    import virus_total_apis
    from virus_total_apis import PublicApi
    VT_LIB = True
    # Version check needs to be higher than 1.0.9
    vt_ver = virus_total_apis.__version__.split('.')
    if int(vt_ver[1]) < 1:
        VT_LIB = False
except ImportError:
    VT_LIB = False


class VirusTotalSearch(Extension):

    extension_name = 'VirusTotalSearch'
    extension_type = 'filedetails'

    def run(self):
        db = Database()
        #self.render_javascript = "function test(){  alert(1); }; test();"
        self.render_javascript = ""
        if not self.config['virustotal']['api_key'] or not VT_LIB:
            self.render_type = 'error'
            self.render_data = "Unable to use Virus Total. No Key or Library Missing. Check the Console for details"

        if 'file_id' in self.request.POST:
            # Get file object from DB
            file_id = self.request.POST['file_id']
            file_object = db.get_filebyid(file_id)
            sha256 = file_object.sha256

            # Init the API with key from config
            vt = PublicApi(self.config.api_key)

            # If we upload
            if 'upload' in self.request.POST:
                response = vt.scan_file(file_object.read(), filename=file_object.filename, from_disk=False)
                if response['results']['response_code'] == 1 and 'Scan request successfully queued' in response['results']['verbose_msg']:
                    print "File Uploaded and pending"
                    state = 'pending'
                else:
                    print response
                    state = 'error'
                vt_results = None

            # Else just get the results
            else:

                # get results from VT
                response = vt.get_file_report(sha256)

                vt_results = {}

                # Valid response
                if response['response_code'] == 200:
                    print "Valid Response from server"

                #  Not present in data set prompt to uploads
                if response['results']['response_code'] == 0:
                    state = 'missing'


                # Still Pending
                elif response['results']['response_code'] == -2:
                    # Still Pending
                    state = 'pending'

                # Results availiable
                elif response['results']['response_code'] == 1:
                    vt_results['permalink'] = response['results']['permalink']
                    vt_results['total'] = response['results']['total']
                    vt_results['positives'] = response['results']['positives']
                    vt_results['scandate'] = response['results']['scan_date']
                    vt_results['scans'] = response['results']['scans']
                    # Store the results in datastore
                    state = 'complete'

            store_data = {'file_id': file_id, 'vt': vt_results, 'state': state}
            db.create_datastore(store_data)

            self.render_type = 'file'
            self.render_data = {'VirusTotalSearch': {'state': state, 'vt_results': vt_results, 'file_id': file_id}}


    def display(self):
        db = Database()
        file_id = self.request.POST['file_id']
        file_datastore = db.search_datastore({'file_id': file_id})
        vt_results = None
        state = 'Not Checked'
        for row in file_datastore:

            if 'vt' in row:
                vt_results = row['vt']
                state = 'complete'

        self.render_data = {'VirusTotalSearch': {'state': state, 'vt_results': vt_results, 'file_id': file_id}}

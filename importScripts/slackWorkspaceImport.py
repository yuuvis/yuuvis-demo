import os
from os.path import isfile, isdir, join, basename
import json
from datetime import datetime, timedelta, timezone
import requests
from processInvoiceContent import extract_total_from_invoice_text
import time as timer

key = "Your_API_Key_Here"
header_dict = {}

header_dict['Ocp-Apim-Subscription-Key'] = key
base_url = 'https://api.yuuvis.io'

input_path = "../input/"


class Message:
    def __init__(self, author, text, created_at, channel, attachments):
        self.author = author
        self.text = text
        self.created_at = created_at
        self.channel = channel
        self.attachments = attachments

class Attachment:
    def __init__(self, name, type, url):
        self.name = name
        self.type = type
        self.url = url

#establish export file structure
slack_export_root_folder_path = input_path + os.listdir(input_path).pop()
slack_export_root_files = os.listdir(slack_export_root_folder_path)

meta_files = [f for f in slack_export_root_files if isfile(join(slack_export_root_folder_path, f))]
channel_dirs = [f for f in slack_export_root_files if isdir(join(slack_export_root_folder_path, f))]

print(slack_export_root_folder_path)
print(slack_export_root_files)
print(channel_dirs)

#retrieve file paths for each channel
input_json_file_paths = {}
for channel_dir in channel_dirs:
    input_json_file_paths[channel_dir] = []
    channel_dirPath = join(slack_export_root_folder_path, channel_dir)
    for input_file_name in os.listdir(channel_dirPath):
        input_json_file_paths[channel_dir].append(join(channel_dirPath, input_file_name))

#print(input_json_file_paths)

epoch = datetime(1601, 1, 1)

for channel_dir in channel_dirs:

    messages = []
    print(f'gathering messages for channel {channel_dir}')
    for chat_log_file in input_json_file_paths[channel_dir]:
        date = basename(chat_log_file).split('.')[0]

        with open(chat_log_file, 'r') as inputFile:

            test_slack_chat_log = json.load(inputFile)
            for post in test_slack_chat_log:
                timestamp = (epoch + timedelta(microseconds = float(post['ts'])))
                time = timestamp.time().strftime("%H:%M:%S")

                created_at = date+"T"+time

                message = Message(post['user'], post['text'], created_at, channel_dir, [])
                if 'files' in post:
                    file_attachments = []
                    for file in post['files']:
                        file_attachments.append(Attachment(file['name'], file['mimetype'], file['url_private_download']))
                    message.attachments = file_attachments
                messages.append(message)

    len_messages = len(messages)
    print(f'importing {len_messages} messages')
    for index_message, message in enumerate(messages):
        #create message object
        message_object = {}
        message_properties = {}
        message_properties["system:objectTypeId"] = {"value": "message"}
        message_properties["author"] = {"value": message.author}
        message_properties["text"] = {"value": message.text}
        message_properties["timestamp"] = {"value": message.created_at}
        message_properties["numOfAttachments"] = {"value": str(len(message.attachments))}
        message_object["properties"] = message_properties

        #import message object
        print(f'importing message {index_message}')
        request_body_message = {
            'data': ('message.json', json.dumps({'objects': [message_object]}), 'application/json')
        }
        response_message = requests.post(str(base_url+'/dms-core/objects'), files = request_body_message, headers=header_dict)

        if response_message.status_code != 200:
            print({'objects': [message_object]})
            print(response_message.content)
        else:
            response_message_json = response_message.json()
            message_id = response_message_json['objects'][0]['properties']['system:objectId']['value']

            if len(message.attachments)>0:
                #create attachment objects objects if attachments exist
                attachment_ids = []
                for index_attachment, attachment in enumerate(message.attachments):
                    attachment_object = {}
                    attachment_properties = {}
                    attachment_properties["system:objectTypeId"] = {"value": "attachment"}
                    attachment_properties["timestamp"] = {"value": message.created_at}
                    attachment_properties["Name"] = {"value": attachment.name}
                    attachment_properties["text"] = {"value": message.text}
                    attachment_properties["author"] = {"value": message.author}
                    attachment_properties["messageId"] = {"value": message_id}
                    attachment_object["properties"] = attachment_properties

                    attachment_object["contentStreams"] = [{
                        "fileName": attachment.name,
                        "mimeType": attachment.type,
                        "cid": "cid_63apple"
                    }]

                    #import attachment object
                    print(f'importing attachment {index_attachment} of message {index_message}')

                    print('fetching binary content from slack servers')
                    response_attachment_file = requests.get(attachment.url)

                    if response_attachment_file.status_code != 200:
                        print(response_message.content)
                    else:
                        request_body_attachment = {
                            'data': ('attachment.json', json.dumps({'objects': [attachment_object]}), 'application/json'),
                            'cid_63apple': (attachment.name, response_attachment_file.content , attachment.type)
                        }

                        response_attachment = requests.post(str(base_url+'/dms-core/objects'), files = request_body_attachment, headers = header_dict)

                        if response_attachment.status_code != 200:
                            print({'objects': [message_object]})
                            print(response_message.content)
                        else:
                            timer.sleep(1)
                            response_attachment_json = response_attachment.json()
                            attachment_id = response_attachment_json['objects'][0]['properties']['system:objectId']['value']
                            attachment_ids.append(attachment_id)

                            print(f'processing attachment {index_attachment} text content')
                            #retrieve text rendition
                            response_rendition = requests.get(str(base_url+'/dms-view/objects/'+attachment_id+'/contents/renditions/text'), headers=header_dict)
                            timer.sleep(4)
                            total = extract_total_from_invoice_text(response_rendition.text)

                            print(f'determined invoice with total: {total}')
                            if total > 0:
                                invoice_patch_object = {}
                                invoice_patch_properties = {}
                                invoice_patch_properties["total"] = {"value": total}
                                invoice_patch_object["properties"] = invoice_patch_properties
                                response_patch = requests.patch(str(base_url+'/dms-core/objects/'+attachment_id), data=json.dumps({'objects':[invoice_patch_object]}) ,headers=header_dict)
                print(message_id, attachment_ids)

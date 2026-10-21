# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import os

from semantic_kernel.contents.chat_history import ChatHistory


class ChatContext:
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.chat_history = ChatHistory()
        self.patient_id = None
        self.patient_data = []
        self.display_blob_urls = []
        self.display_image_urls = []
        self.display_clinical_trials = []
        self.output_data = []
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.healthcare_agents = {}

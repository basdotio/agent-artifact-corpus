import asyncio
from typing import Any
from mcp import stdio_server
from mcp.server import Server as MCPServer
import mcp.types as types 

from dingtalk.dingtalk_server import DingtalkServer

class DingtalkIMServer(DingtalkServer):
    def __init__(self):
        super().__init__()

    async def add_group_members_old(self, open_conversation_id: str, user_ids: str) -> str:
        """
        新增群成员（旧版SDK）.

        args:
            open_conversation_id (str): 群ID
            user_ids (str): 批量增加的成员userid，多个userid之间使用英文逗号分隔，最多传100个
        """
        url = "https://oapi.dingtalk.com/topapi/im/chat/scenegroup/member/add"
        data = {
            "open_conversation_id": open_conversation_id,
            "user_ids": user_ids
        }
        return await self.post_old(url, json=data)


    async def send_work_notification_old(
        self,
        agent_id: int,
        msg: dict,
        userid_list: str = None,
        dept_id_list: str = None,
        to_all_user: bool = False
    ) -> str:
        """
        发送工作通知消息（旧版SDK）.

        args:
            agent_id (int): 发送消息时使用的微应用的AgentID。
            msg (dict): 消息内容，支持多种工作通知类型。
            userid_list (str, optional): 接收者的userid列表，最大用户列表长度100。默认为None。
            dept_id_list (str, optional): 接收者的部门id列表，最大列表长度20。默认为None。
            to_all_user (bool, optional): 是否发送给企业全部用户。默认为False。
        """
        url = "https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2"
        data = {
            "agent_id": agent_id,
            "msg": msg,
            "userid_list": userid_list,
            "dept_id_list": dept_id_list,
            "to_all_user": to_all_user
        }
        return await self.post_old(url, json=data)


    async def batch_recall_robot_messages(self, robotCode: str, processQueryKeys: list) -> str:
        """
        批量撤回人与机器人会话中机器人消息.

        args:
            robotCode (str): 机器人的编码，需要与批量发送接口中使用的robotCode保持一致。
            processQueryKeys (list): 消息唯一标识列表，每次最多传20个。
        """
        url = "https://api.dingtalk.com/v1.0/robot/otoMessages/batchRecall"
        data = {
            "robotCode": robotCode,
            "processQueryKeys": processQueryKeys
        }
        return await self.post_new(url, json=data)


    async def set_group_administrators(self, openConversationId: str, userIds: list, role: int) -> str:
        """
        批量设置企业群管理员。

        args:
            openConversationId (str): 开放群ID。
            userIds (list): 企业员工userid列表。
            role (int): 设置类型，2为添加为管理员，3为删除该管理员。
        """
        url = "https://api.dingtalk.com/v1.0/im/subAdministrators"
        data = {
            "openConversationId": openConversationId,
            "userIds": userIds,
            "role": role
        }
        return await self.post_new(url, json=data)


    async def batch_recall_robot_messages(self, openConversationId: str, robotCode: str, processQueryKeys: list) -> str:
        """
        批量撤回人与人会话中机器人消息.

        args:
            openConversationId (str): 会话ID，需与发送消息接口的openConversationId保持一致。
            robotCode (str): 机器人编码，需与发送消息接口的robotCode保持一致。
            processQueryKeys (list): 消息ID列表。
        """
        url = "https://api.dingtalk.com/v1.0/robot/privateChatMessages/batchRecall"
        data = {
            "openConversationId": openConversationId,
            "robotCode": robotCode,
            "processQueryKeys": processQueryKeys
        }
        return await self.post_new(url, json=data)


    async def get_message_read_status(self, robotCode: str, processQueryKey: str) -> str:
        """
        批量查询人与机器人会话机器人消息是否已读.

        args:
            robotCode (str): 机器人的编码，详情参考机器人 ID。
            processQueryKey (str): 消息唯一标识，可通过批量发送人与机器人会话中机器人消息接口返回参数中 processQueryKey 字段获取。
        """
        url = f"https://api.dingtalk.com/v1.0/robot/oToMessages/readStatus?robotCode={robotCode}&processQueryKey={processQueryKey}"
        return await self.get_new(url)


    async def query_group_message_read_status(self, processQueryKey: str, openConversationId: str = None, robotCode: str = None, maxResults: int = None, nextToken: str = None) -> str:
        """
        查询企业机器人群聊消息用户已读状态.

        args:
            processQueryKey (str): 消息唯一标识，必填。
            openConversationId (str, optional): 群ID，与发送消息时使用的openConversationId一致。
            robotCode (str, optional): 机器人编码，与发送消息时使用的robotCode一致。
            maxResults (int, optional): 分页查询每页的数量，最大值200。
            nextToken (str, optional): 分页游标，置空表示从首页开始查询。
        """
        url = "https://api.dingtalk.com/v1.0/robot/groupMessages/query"
        data = {
            "processQueryKey": processQueryKey,
            "openConversationId": openConversationId,
            "robotCode": robotCode,
            "maxResults": maxResults,
            "nextToken": nextToken
        }
        return await self.post_new(url, json=data)


    async def batch_send_robot_messages(self, robotCode: str, userIds: list, msgKey: str, msgParam: str) -> str:
        """
        批量发送人与机器人会话中机器人消息.

        args:
            robotCode (str): 机器人的编码，仅支持企业内部应用机器人调用。
            userIds (list): 接收机器人消息的用户的userId列表，每次最多传20个。
            msgKey (str): 消息模板key。
            msgParam (str): 消息模板参数。
        """
        url = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"
        data = {
            "robotCode": robotCode,
            "userIds": userIds,
            "msgKey": msgKey,
            "msgParam": msgParam
        }
        return await self.post_new(url, json=data)


    async def clear_robot_shortcut(self, robotCode: str) -> str:
        """
        清空单聊机器人快捷入口.

        args:
            robotCode (str): 机器人的编码，参见机器人名词表-robotCode内容，获取robotCode。
        """
        url = "https://api.dingtalk.com/v1.0/robot/plugins/clear"
        data = {"robotCode": robotCode}
        return await self.post_new(url, json=data)


    async def close_interactive_card_top_box(self, outTrackId: str, conversationType: int, openConversationId: str = None, userId: str = None, unionId: str = None, robotCode: str = None, coolAppCode: str = None, groupTemplateId: str = None) -> str:
        """
        关闭互动卡片吊顶.

        args:
            outTrackId (str): 唯一标识一张卡片的外部ID，最大长度64。
            conversationType (int): 会话类型：1-群聊，2-单聊助手。
            openConversationId (str, optional): 会话ID，群聊时必传。
            userId (str, optional): 用户userId，单聊助手时与unionId二选一必填。
            unionId (str, optional): 用户unionId，单聊助手时与userId二选一必填。
            robotCode (str, optional): 机器人编码，单聊助手时必填。
            coolAppCode (str, optional): 酷应用编码，安装群聊酷应用的群时必填。
            groupTemplateId (str, optional): 群模板ID，基于群模板创建的群时必填。
        """
        url = "https://api.dingtalk.com/v2.0/im/topBoxes/close"
        data = {
            "outTrackId": outTrackId,
            "conversationType": conversationType,
            "openConversationId": openConversationId,
            "userId": userId,
            "unionId": unionId,
            "robotCode": robotCode,
            "coolAppCode": coolAppCode,
            "groupTemplateId": groupTemplateId
        }
        return await self.post_new(url, json=data)


    async def create_group(self, title: str, template_id: str, owner_user_id: str, user_ids: list = None, subadmin_ids: list = None, uuid: str = None, icon: str = None, mention_all_authority: int = 0, show_history_type: int = 0, validation_type: int = 0, searchable: int = 0, chat_banned_type: int = 0, management_type: int = 0, only_admin_can_ding: int = 0, all_members_can_create_mcs_conf: int = 1, all_members_can_create_calendar: int = 0, group_email_disabled: int = 0, only_admin_can_set_msg_top: int = 0, add_friend_forbidden: int = 0, group_live_switch: int = 1, members_to_admin_chat: int = 0) -> str:
        """
        根据群模板ID创建群。

        args:
            title (str): 群名称，最长不超过30字符。
            template_id (str): 群模板ID。
            owner_user_id (str): 群主的userid。
            user_ids (list, optional): 群成员userid列表，最多传999个。
            subadmin_ids (list, optional): 群管理员userid列表。
            uuid (str, optional): 建群去重的业务ID，建议长度在64字符以内。
            icon (str, optional): 群头像，格式为mediaId。
            mention_all_authority (int, optional): @all权限，默认0（所有人可@all）。
            show_history_type (int, optional): 新成员是否可查看聊天历史消息，默认0（不可查看）。
            validation_type (int, optional): 入群是否需要验证，默认0（不验证）。
            searchable (int, optional): 群是否可搜索，默认0（不可搜索）。
            chat_banned_type (int, optional): 是否开启群禁言，默认0（不禁言）。
            management_type (int, optional): 管理类型，默认0（所有人可管理）。
            only_admin_can_ding (int, optional): 群内发DING权限，默认0（所有人可发DING）。
            all_members_can_create_mcs_conf (int, optional): 群会议权限，默认1（所有人可发起视频和语音会议）。
            all_members_can_create_calendar (int, optional): 群日历设置项，默认0（非好友/同事不可发起钉钉日程）。
            group_email_disabled (int, optional): 是否禁止发送群邮件，默认0（允许发送）。
            only_admin_can_set_msg_top (int, optional): 置顶群消息权限，默认0（所有人可置顶群消息）。
            add_friend_forbidden (int, optional): 群成员私聊权限，默认0（所有人可私聊）。
            group_live_switch (int, optional): 群直播权限，默认1（群内任意成员可发起群直播）。
            members_to_admin_chat (int, optional): 是否禁止非管理员向管理员发起单聊，默认0（允许）。
        """
        url = "https://oapi.dingtalk.com/topapi/im/chat/scenegroup/create"
        data = {
            "title": title,
            "template_id": template_id,
            "owner_user_id": owner_user_id,
            "user_ids": ",".join(user_ids) if user_ids else None,
            "subadmin_ids": ",".join(subadmin_ids) if subadmin_ids else None,
            "uuid": uuid,
            "icon": icon,
            "mention_all_authority": mention_all_authority,
            "show_history_type": show_history_type,
            "validation_type": validation_type,
            "searchable": searchable,
            "chat_banned_type": chat_banned_type,
            "management_type": management_type,
            "only_admin_can_ding": only_admin_can_ding,
            "all_members_can_create_mcs_conf": all_members_can_create_mcs_conf,
            "all_members_can_create_calendar": all_members_can_create_calendar,
            "group_email_disabled": group_email_disabled,
            "only_admin_can_set_msg_top": only_admin_can_set_msg_top,
            "add_friend_forbidden": add_friend_forbidden,
            "group_live_switch": group_live_switch,
            "members_to_admin_chat": members_to_admin_chat
        }
        # 移除值为None的字段
        data = {k: v for k, v in data.items() if v is not None}
        return await self.post_old(url, json=data)


    async def create_and_open_interactive_card(self, cardTemplateId: str, outTrackId: str, conversationType: int, 
                                            cardData: dict, callbackRouteKey: str = None, userIdPrivateDataMap: dict = None, 
                                            unionIdPrivateDataMap: dict = None, cardSettings: dict = None, 
                                            openConversationId: str = None, userId: str = None, unionId: str = None, 
                                            robotCode: str = None, coolAppCode: str = None, groupTemplateId: str = None, 
                                            receiverUserIdList: list = None, receiverUnionIdList: list = None, 
                                            expiredTime: int = None, platforms: str = None) -> str:
        """
        创建并开启互动卡片吊顶.

        args:
            cardTemplateId (str): 互动卡片的消息模板ID。
            outTrackId (str): 唯一标识一张卡片的外部ID，最大长度64。
            conversationType (int): 会话类型：1-群聊，2-单聊助手。
            cardData (dict): 卡片数据。
            callbackRouteKey (str, optional): 控制卡片回调时的路由Key。
            userIdPrivateDataMap (dict, optional): 卡片模板userId差异用户参数。
            unionIdPrivateDataMap (dict, optional): 卡片模板unionId差异用户参数。
            cardSettings (dict, optional): 卡片设置项。
            openConversationId (str, optional): 群聊会话ID。
            userId (str, optional): 用户userId（单聊助手时必填）。
            unionId (str, optional): 用户unionId（单聊助手时必填）。
            robotCode (str, optional): 机器人编码（单聊助手时必填）。
            coolAppCode (str, optional): 酷应用编码（安装群聊酷应用的群时必填）。
            groupTemplateId (str, optional): 群模板ID（基于群模板创建的群时必填）。
            receiverUserIdList (list, optional): 吊顶可见者userId列表。
            receiverUnionIdList (list, optional): 吊顶可见者unionId列表。
            expiredTime (int, optional): 吊顶的过期时间，毫秒级时间戳。
            platforms (str, optional): 期望吊顶的端。
        """
        url = "https://api.dingtalk.com/v2.0/im/topBoxes"
        data = {
            "cardTemplateId": cardTemplateId,
            "outTrackId": outTrackId,
            "conversationType": conversationType,
            "cardData": cardData,
            "callbackRouteKey": callbackRouteKey,
            "userIdPrivateDataMap": userIdPrivateDataMap,
            "unionIdPrivateDataMap": unionIdPrivateDataMap,
            "cardSettings": cardSettings,
            "openConversationId": openConversationId,
            "userId": userId,
            "unionId": unionId,
            "robotCode": robotCode,
            "coolAppCode": coolAppCode,
            "groupTemplateId": groupTemplateId,
            "receiverUserIdList": receiverUserIdList,
            "receiverUnionIdList": receiverUnionIdList,
            "expiredTime": expiredTime,
            "platforms": platforms
        }
        return await self.post_new(url, json=data)


    async def create_group(self, name: str, owner: str, useridlist: list, showHistoryType: int = None, searchable: int = None, validationType: int = None, mentionAllAuthority: int = None, managementType: int = None, chatBannedType: int = None) -> str:
        """
        创建内部群会话.

        args:
            name (str): 群名称，长度限制为1~20个字符。
            owner (str): 群主的userId。
            useridlist (list): 群成员列表，每次最多支持40人，群人数上限为1000。
            showHistoryType (int): 新成员是否可查看100条历史消息（1：可查看，0：不可查看）。
            searchable (int): 群是否可以被搜索（0：不可搜索，1：可搜索）。
            validationType (int): 入群是否需要验证（0：不验证，1：入群验证）。
            mentionAllAuthority (int): @all 使用范围（0：所有人可使用，1：仅群主可@all）。
            managementType (int): 群管理类型（0：所有人可管理，1：仅群主可管理）。
            chatBannedType (int): 是否开启群禁言（0：不禁言，1：全员禁言）。
        """
        url = "https://oapi.dingtalk.com/chat/create"
        data = {
            "name": name,
            "owner": owner,
            "useridlist": useridlist,
            "showHistoryType": showHistoryType,
            "searchable": searchable,
            "validationType": validationType,
            "mentionAllAuthority": mentionAllAuthority,
            "managementType": managementType,
            "chatBannedType": chatBannedType
        }
        # 移除值为None的参数
        data = {k: v for k, v in data.items() if v is not None}
        return await self.post_old(url, json=data)


    async def close_group_template(self, owner_user_id: str, template_id: str, open_conversation_id: str) -> str:
        """
        停用群模板.

        args:
            owner_user_id (str): 群主userid。
            template_id (str): 群模板id。
            open_conversation_id (str): 群ID。
        """
        url = "https://oapi.dingtalk.com/topapi/im/chat/scenegroup/template/close"
        data = {
            "owner_user_id": owner_user_id,
            "template_id": template_id,
            "open_conversation_id": open_conversation_id
        }
        return await self.post_old(url, json=data)


    async def download_robot_message_file(self, downloadCode: str, robotCode: str) -> str:
        """
        下载机器人接收消息的文件内容.

        args:
            downloadCode (str): 用户向机器人发送文件消息后，机器人回调给开发者消息中的下载码。
            robotCode (str): 机器人的编码。
        """
        url = "https://api.dingtalk.com/v1.0/robot/messageFiles/download"
        data = {
            "downloadCode": downloadCode,
            "robotCode": robotCode
        }
        return await self.post_new(url, json=data)


    async def enable_group_template(self, owner_user_id: str, template_id: str, open_conversation_id: str) -> str:
        """
        启用群模板.

        args:
            owner_user_id (str): 群主的userid。
            template_id (str): 群模板id。
            open_conversation_id (str): 群ID。
        """
        url = "https://oapi.dingtalk.com/topapi/im/chat/scenegroup/template/apply"
        data = {
            "owner_user_id": owner_user_id,
            "template_id": template_id,
            "open_conversation_id": open_conversation_id
        }
        return await self.post_old(url, json=data)


    async def recall_group_message(self, openConversationId: str, robotCode: str, processQueryKeys: list) -> str:
        """
        企业机器人撤回内部群消息.

        args:
            openConversationId (str): 群ID，需要与机器人发送群聊消息接口时使用的openConversationId一致。
            robotCode (str): 机器人的编码，需要与机器人发送群聊消息接口时使用的robotCode一致。
            processQueryKeys (list): 消息ID列表，通过机器人发送群聊消息接口返回参数processQueryKey字段中获取。
        """
        url = "https://api.dingtalk.com/v1.0/robot/groupMessages/recall"
        data = {
            "openConversationId": openConversationId,
            "robotCode": robotCode,
            "processQueryKeys": processQueryKeys
        }
        return await self.post_new(url, json=data)


    async def get_work_notification_send_result(self, agent_id: int, task_id: int) -> str:
        """
        获取工作通知消息的发送结果.

        args:
            agent_id (int): 发送消息时使用的微应用的AgentID。
            task_id (int): 发送消息时钉钉返回的任务ID。
        """
        url = "https://oapi.dingtalk.com/topapi/message/corpconversation/getsendresult"
        data = {
            "agent_id": agent_id,
            "task_id": task_id
        }
        return await self.post_old(url, json=data)


    async def update_group_chat_old(self, chatid: str, name: str = None, owner: str = None, ownerType: str = None,
                                    add_useridlist: list = None, del_useridlist: list = None, add_extidlist: list = None,
                                    del_extidlist: list = None, icon: str = None, searchable: int = None,
                                    validationType: int = None, mentionAllAuthority: int = None,
                                    managementType: int = None, chatBannedType: int = None, showHistoryType: int = None,
                                    isBan: bool = None) -> str:
        """
        更新群会话（旧版SDK）.

        args:
            chatid (str): 群会话ID，必填。
            name (str, optional): 群名称，长度限制为1~20个字符。
            owner (str, optional): 群主的userId。
            ownerType (str, optional): 群主类型，可选值：emp（企业员工）、ext（外部联系人）。
            add_useridlist (list, optional): 添加的群成员列表，每次最多支持40人。
            del_useridlist (list, optional): 删除的成员列表。
            add_extidlist (list, optional): 添加的外部联系人成员列表。
            del_extidlist (list, optional): 删除的外部联系人成员列表。
            icon (str, optional): 群头像的mediaId。
            searchable (int, optional): 群是否可以被搜索，0（不可搜索，默认），1（可搜索）。
            validationType (int, optional): 入群是否需要验证，0（不验证，默认），1（入群验证）。
            mentionAllAuthority (int, optional): @all 使用范围，0（所有人可使用，默认），1（仅群主可@all）。
            managementType (int, optional): 群管理类型，0（所有人可管理，默认），1（仅群主可管理）。
            chatBannedType (int, optional): 是否开启群禁言，0（不禁言，默认），1（全员禁言）。
            showHistoryType (int, optional): 新成员是否可查看100条历史消息，0（不可查看，默认），1（可查看）。
            isBan (bool, optional): 是否禁言，true（禁言），false（不禁言）。
        """
        url = "https://oapi.dingtalk.com/chat/update"
        data = {
            "chatid": chatid,
            "name": name,
            "owner": owner,
            "ownerType": ownerType,
            "add_useridlist": add_useridlist,
            "del_useridlist": del_useridlist,
            "add_extidlist": add_extidlist,
            "del_extidlist": del_extidlist,
            "icon": icon,
            "searchable": searchable,
            "validationType": validationType,
            "mentionAllAuthority": mentionAllAuthority,
            "managementType": managementType,
            "chatBannedType": chatBannedType,
            "showHistoryType": showHistoryType,
            "isBan": isBan
        }
        # 移除值为None的字段
        data = {k: v for k, v in data.items() if v is not None}
        return await self.post_old(url, json=data)


    async def recall_work_notification(self, agent_id: int, msg_task_id: int) -> str:
        """
        撤回工作通知消息.

        args:
            agent_id (int): 发送消息时使用的微应用的AgentID。
            msg_task_id (int): 发送消息时钉钉返回的任务ID。
        """
        url = "https://oapi.dingtalk.com/topapi/message/corpconversation/recall"
        data = {
            "agent_id": agent_id,
            "msg_task_id": msg_task_id
        }
        return await self.post_old(url, json=data)


    async def get_chat_info(self, chatid: str) -> str:
        """
        查询群信息.

        args:
            chatid (str): 群会话的ID
        """
        url = "https://oapi.dingtalk.com/chat/get"
        params = {
            "chatid": chatid
        }
        return await self.get_old(url, params=params)


    async def get_group_qrcode(self, chatid: str, userid: str) -> str:
        """
        获取群入群二维码链接.

        args:
            chatid (str): 群会话的chatid
            userid (str): 分享二维码用户的userId
        """
        url = "https://oapi.dingtalk.com/topapi/chat/qrcode/get"
        data = {
            "chatid": chatid,
            "userid": userid
        }
        return await self.post_old(url, json=data)


    async def get_open_conversation_id(self, chatId: str) -> str:
        """
        获取群会话的OpenConversationId.

        args:
            chatId (str): 群会话chatId。
        """
        url = f"https://api.dingtalk.com/v1.0/im/chat/{chatId}/convertToOpenConversationId"
        return await self.post_new(url)


    async def get_bot_list_in_group(self, open_conversation_id: str) -> str:
        """
        获取群内机器人列表.

        args:
            open_conversation_id (str): 群ID，基于群模板创建的群。
        """
        url = "https://api.dingtalk.com/v1.0/robot/getBotListInGroup"
        data = {"openConversationId": open_conversation_id}
        return await self.post_new(url, json=data)


    async def get_send_progress(self, agent_id: int, task_id: int) -> str:
        """
        获取工作通知消息的发送进度.

        args:
            agent_id (int): 发送消息时使用的微应用的AgentID。
            task_id (int): 发送消息时钉钉返回的任务ID。
        """
        url = "https://oapi.dingtalk.com/topapi/message/corpconversation/getsendprogress"
        data = {
            "agent_id": agent_id,
            "task_id": task_id
        }
        return await self.post_old(url, json=data)


    async def get_group_info(self, open_conversation_id: str) -> str:
        """
        查询群信息.

        args:
            open_conversation_id (str): 群ID
        """
        url = "https://oapi.dingtalk.com/topapi/im/chat/scenegroup/get"
        data = {
            "open_conversation_id": open_conversation_id
        }
        return await self.post_old(url, json=data)


    async def query_group_summary(self, open_conversation_id: str, cool_app_code: str = None) -> str:
        """
        查询群简要信息.

        args:
            open_conversation_id (str): 群ID，基于群模板创建的群或安装群聊酷应用的群。
            cool_app_code (str, optional): 群聊酷应用编码，仅安装群聊酷应用的群需要传入。
        """
        url = "https://api.dingtalk.com/v1.0/im/sceneGroups/query"
        data = {
            "openConversationId": open_conversation_id,
            "coolAppCode": cool_app_code
        }
        return await self.post_new(url, json=data)


    async def batch_query_group_members(self, open_conversation_id: str, max_results: int, cool_app_code: str = None, next_token: str = None) -> str:
        """
        批量查询群成员信息.

        args:
            open_conversation_id (str): 群ID，基于群模板创建的群或安装群聊酷应用的群。
            max_results (int): 分页大小。
            cool_app_code (str, optional): 群聊酷应用编码，安装群聊酷应用的群必须传入。
            next_token (str, optional): 分页游标，置空表示从首页开始查询。
        """
        url = "https://api.dingtalk.com/v1.0/im/sceneGroups/members/batchQuery"
        data = {
            "openConversationId": open_conversation_id,
            "maxResults": max_results,
        }
        if cool_app_code:
            data["coolAppCode"] = cool_app_code
        if next_token:
            data["nextToken"] = next_token
        return await self.post_new(url, json=data)


    async def get_group_mute_status(self, userId: str, openConversationId: str) -> str:
        """
        查询群禁言状态.

        args:
            userId (str): 群成员userId。
            openConversationId (str): 群ID，通过创建群接口获取open_conversation_id字段值。
        """
        url = f"https://api.dingtalk.com/v1.0/im/sceneGroups/muteSettings"
        params = {
            "userId": userId,
            "openConversationId": openConversationId
        }
        return await self.get_new(url, params=params)


    async def query_robot_message_read_list(self, processQueryKey: str, openConversationId: str = None, robotCode: str = None, maxResults: int = None, nextToken: str = None) -> str:
        """
        查询人与人会话中机器人消息已读列表.

        args:
            processQueryKey (str): 消息id，必填。
            openConversationId (str, optional): 人与人单聊开放会话ID。
            robotCode (str, optional): 机器人的编码。
            maxResults (int, optional): 分页查询每页的数量。
            nextToken (str, optional): 加密的分页凭证，首次查询不填。
        """
        url = "https://api.dingtalk.com/v1.0/robot/privateChatMessages/query"
        data = {
            "processQueryKey": processQueryKey,
            "openConversationId": openConversationId,
            "robotCode": robotCode,
            "maxResults": maxResults,
            "nextToken": nextToken
        }
        return await self.post_new(url, json=data)


    async def query_robot_plugin_shortcut(self, robotCode: str) -> str:
        """
        查询单聊机器人的快捷入口.

        args:
            robotCode (str): 机器人的编码，参见机器人名词表-robotCode内容，获取robotCode。
        """
        url = "https://api.dingtalk.com/v1.0/robot/plugins/query"
        data = {
            "robotCode": robotCode
        }
        return await self.post_new(url, json=data)


    async def send_ding_message(self, robotCode: str, remindType: int, receiverUserIdList: list, content: str) -> str:
        """
        发送DING消息专业版去升级.

        args:
            robotCode (str): 发DING消息的机器人ID。
            remindType (int): DING消息类型。1：应用内DING，2：短信DING，3：电话DING。
            receiverUserIdList (list): 接收人userId列表。
            content (str): DING消息内容。
        """
        url = "https://api.dingtalk.com/v1.0/robot/ding/send"
        data = {
            "robotCode": robotCode,
            "remindType": remindType,
            "receiverUserIdList": receiverUserIdList,
            "content": content
        }
        return await self.post_new(url, json=data)


    async def recall_ding_message(self, robotCode: str, openDingId: str) -> str:
        """
        撤回已经发送的DING消息。

        args:
            robotCode (str): 发送DING消息的机器人ID。
            openDingId (str): 需要被撤回的DING消息ID。
        """
        url = "https://api.dingtalk.com/v1.0/robot/ding/recall"
        data = {
            "robotCode": robotCode,
            "openDingId": openDingId
        }
        return await self.post_new(url, json=data)


    async def delete_group_members(self, open_conversation_id: str, user_ids: str) -> str:
        """
        删除群成员.

        args:
            open_conversation_id (str): 群ID
            user_ids (str): 批量删除的成员userid，多个userid之间使用英文逗号分隔，最多传100个
        """
        url = "https://oapi.dingtalk.com/topapi/im/chat/scenegroup/member/delete"
        data = {
            "open_conversation_id": open_conversation_id,
            "user_ids": user_ids
        }
        return await self.post_old(url, json=data)


    async def update_group(self, open_conversation_id: str, title: str = None, owner_user_id: str = None, icon: str = None, mention_all_authority: int = None, show_history_type: int = None, validation_type: int = None, searchable: int = None, chat_banned_type: int = None, management_type: int = None, only_admin_can_ding: int = None, all_members_can_create_mcs_conf: int = None, all_members_can_create_calendar: int = None, group_email_disabled: int = None, only_admin_can_set_msg_top: int = None, add_friend_forbidden: int = None, group_live_switch: int = None, members_to_admin_chat: int = None, plugin_customize_verify: int = None) -> str:
        """
        更新群信息.

        args:
            open_conversation_id (str): 群ID，必填。
            title (str, optional): 群名称。
            owner_user_id (str, optional): 群主的userId。
            icon (str, optional): 群头像，格式为mediaId。
            mention_all_authority (int, optional): @all权限（0:所有人可@all, 1:仅群主可@all）。
            show_history_type (int, optional): 新成员是否可查看聊天历史消息（0:不可以, 1:可以）。
            validation_type (int, optional): 入群验证（0:不需要验证, 1:入群验证）。
            searchable (int, optional): 群是否可搜索（0:不可搜索, 1:可搜索）。
            chat_banned_type (int, optional): 群是否开启禁言（0:不禁言, 1:全员禁言）。
            management_type (int, optional): 管理类型（0:所有人可管理, 1:仅群主可管理）。
            only_admin_can_ding (int, optional): 群内发DING权限（0:所有人可发DING, 1:仅群主和管理员可发DING）。
            all_members_can_create_mcs_conf (int, optional): 群会议权限（0:仅群主和管理员可发起视频和语音会议, 1:所有人可发起视频和语音会议）。
            all_members_can_create_calendar (int, optional): 群日历设置项（0:非好友/同事的成员不可发起钉钉日程, 1:非好友/同事的成员可以发起钉钉日程）。
            group_email_disabled (int, optional): 是否禁止发送群邮件（0:群内成员可以对本群发送群邮件, 1:群内成员不可对本群发送群邮件）。
            only_admin_can_set_msg_top (int, optional): 置顶群消息权限（0:所有人可置顶群消息, 1:仅群主和管理员可置顶群消息）。
            add_friend_forbidden (int, optional): 群成员私聊权限（0:所有人可私聊, 1:普通群成员之间不能够加好友、单聊，且部分功能使用受限）。
            group_live_switch (int, optional): 群直播权限（0:仅群主与管理员可发起直播, 1:群内任意成员可发起群直播）。
            members_to_admin_chat (int, optional): 是否禁止非管理员向管理员发起单聊（0:非管理员可以向管理员发起单聊, 1:禁止非管理员向管理员发起单聊）。
            plugin_customize_verify (int, optional): 自定义群插件是否需要群主和管理员审批（0:不需要审批, 1:需要审批）。
        """
        url = "https://oapi.dingtalk.com/topapi/im/chat/scenegroup/update"
        data = {
            "open_conversation_id": open_conversation_id,
            "title": title,
            "owner_user_id": owner_user_id,
            "icon": icon,
            "mention_all_authority": mention_all_authority,
            "show_history_type": show_history_type,
            "validation_type": validation_type,
            "searchable": searchable,
            "chat_banned_type": chat_banned_type,
            "management_type": management_type,
            "only_admin_can_ding": only_admin_can_ding,
            "all_members_can_create_mcs_conf": all_members_can_create_mcs_conf,
            "all_members_can_create_calendar": all_members_can_create_calendar,
            "group_email_disabled": group_email_disabled,
            "only_admin_can_set_msg_top": only_admin_can_set_msg_top,
            "add_friend_forbidden": add_friend_forbidden,
            "group_live_switch": group_live_switch,
            "members_to_admin_chat": members_to_admin_chat,
            "plugin_customize_verify": plugin_customize_verify
        }
        return await self.post_old(url, json=data)


    async def get_group_template_robots(self, robotCode: str = None, openConversationId: str = None) -> str:
        """
        查询群内群模版机器人信息.

        args:
            robotCode (str, optional): 机器人的编码。登录开发者后台 > 开放能力 > 场景群 > 机器人查看id。
            openConversationId (str, optional): 群ID。可通过创建群接口获取open_conversation_id参数值。
        """
        url = "https://api.dingtalk.com/v1.0/im/sceneGroups/template/robots"
        params = {}
        if robotCode:
            params["robotCode"] = robotCode
        if openConversationId:
            params["openConversationId"] = openConversationId
        return await self.get_new(url, params=params)


    async def send_group_assistant_message_old(
        self,
        target_open_conversation_id: str,
        msg_template_id: str,
        msg_param_map: dict = None,
        msg_media_id_param_map: dict = None,
        receiver_user_ids: list = None,
        receiver_union_ids: list = None,
        receiver_mobiles: list = None,
        at_mobiles: list = None,
        at_users: list = None,
        is_at_all: bool = False,
        robot_code: str = None
    ) -> str:
        """
        发送群助手消息（旧版SDK）.

        args:
            target_open_conversation_id (str): 群ID。
            msg_template_id (str): 消息模板ID。
            msg_param_map (dict, optional): 消息模板内容替换参数，普通文本类型。
            msg_media_id_param_map (dict, optional): 消息模板内容替换参数，多媒体类型。
            receiver_user_ids (list, optional): 消息接收人userId列表。
            receiver_union_ids (list, optional): 消息接收人unionId列表。
            receiver_mobiles (list, optional): 消息接收人手机号列表。
            at_mobiles (list, optional): @人的手机号列表。
            at_users (list, optional): @人的userid列表。
            is_at_all (bool, optional): 是否@所有人。
            robot_code (str): 机器人编码。
        """
        url = "https://oapi.dingtalk.com/topapi/im/chat/scencegroup/message/send_v2"
        data = {
            "target_open_conversation_id": target_open_conversation_id,
            "msg_template_id": msg_template_id,
            "msg_param_map": msg_param_map,
            "msg_media_id_param_map": msg_media_id_param_map,
            "receiver_user_ids": receiver_user_ids,
            "receiver_union_ids": receiver_union_ids,
            "receiver_mobiles": receiver_mobiles,
            "at_mobiles": at_mobiles,
            "at_users": at_users,
            "is_at_all": is_at_all,
            "robot_code": robot_code
        }
        return await self.post_old(url, json=data)


    async def update_group_nick(self, userid: str, chatid: str, group_nick: str) -> str:
        """
        更新群成员的群昵称.

        args:
            userid (str): 要更改群昵称的群成员userId
            chatid (str): 群会话ID
            group_nick (str): 该成员在群中的昵称
        """
        url = "https://oapi.dingtalk.com/topapi/chat/updategroupnick"
        data = {
            "userid": userid,
            "chatid": chatid,
            "group_nick": group_nick
        }
        return await self.post_old(url, json=data)


    async def update_group_admin_old(self, chatid: str, userids: str, role: int) -> str:
        """
        更新群管理员（旧版SDK）.

        args:
            chatid (str): 群会话ID
            userids (str): 群成员userId
            role (int): 角色，2表示添加为管理员，3表示删除该管理员
        """
        url = "https://oapi.dingtalk.com/topapi/chat/subadmin/update"
        data = {
            "chatid": chatid,
            "userids": userids,
            "role": role
        }
        return await self.post_old(url, json=data)


    async def set_group_member_mute_status(self, user_id_list: list, open_conversation_id: str, mute_status: int, mute_duration: int) -> str:
        """
        设置群成员禁言状态.

        args:
            user_id_list (list): 需要禁言或取消禁言的群成员userId列表。
            open_conversation_id (str): 群ID，通过创建群接口获取open_conversation_id参数值。
            mute_status (int): 禁言状态，0表示取消禁言，1表示禁言。
            mute_duration (int): 禁言持续时长，单位：毫秒。
        """
        url = "https://api.dingtalk.com/v1.0/im/sceneGroups/muteMembers/set"
        data = {
            "userIdList": user_id_list,
            "openConversationId": open_conversation_id,
            "muteStatus": mute_status,
            "muteDuration": mute_duration
        }
        return await self.post_new(url, json=data)


    async def set_group_member_private_chat(self, chatid: str, is_prohibit: bool) -> str:
        """
        设置禁止群成员私聊.

        args:
            chatid (str): 企业会话ID
            is_prohibit (bool): 是否开启禁止开关，true为开启，false为关闭
        """
        url = "https://oapi.dingtalk.com/topapi/chat/member/friendswitch/update"
        data = {
            "chatid": chatid,
            "is_prohibit": is_prohibit
        }
        return await self.post_old(url, json=data)


    async def set_robot_plugin(self, robotCode: str = None, pluginInfoList: list = None) -> str:
        """
        设置单聊机器人的快捷入口.

        args:
            robotCode (str, optional): 机器人的编码，参见机器人名词表-robotCode内容.
            pluginInfoList (list, optional): 插件列表，包含以下字段：
                - pcUrl (str, optional): pc端会话快捷入口跳转链接.
                - mobileUrl (str, optional): 手机端快捷入口跳转链接.
                - name (str): 快捷入口的名称，支持国际化形式，如 {"en_US":"test123","zh_CN":"测试123"}.
                - icon (str): 快捷入口的图标id，可通过调用上传媒体文件接口获取参数字段 mediaId.
        """
        url = "https://api.dingtalk.com/v1.0/robot/plugins/set"
        data = {
            "robotCode": robotCode,
            "pluginInfoList": pluginInfoList
        }
        return await self.post_new(url, json=data)


    async def send_group_message(self, msgParam: str, msgKey: str, openConversationId: str = None, robotCode: str = None, coolAppCode: str = None) -> str:
        """
        机器人发送群聊消息.

        args:
            msgParam (str): 消息模板参数，长度限制 15000 字节以内。
            msgKey (str): 消息模板 key。
            openConversationId (str, optional): 会话 ID，根据群类型不同获取方式不同。
            robotCode (str, optional): 机器人的编码。
            coolAppCode (str, optional): 群聊酷应用编码，使用群聊酷应用方式安装机器人时必填。
        """
        url = "https://api.dingtalk.com/v1.0/robot/groupMessages/send"
        data = {
            "msgParam": msgParam,
            "msgKey": msgKey,
            "openConversationId": openConversationId,
            "robotCode": robotCode,
            "coolAppCode": coolAppCode
        }
        return await self.post_new(url, json=data)


    async def send_private_chat_message(self, msgParam: str, msgKey: str, openConversationId: str, robotCode: str, coolAppCode: str) -> str:
        """
        人与人会话中机器人发送普通消息.

        args:
            msgParam (str): 消息模板参数.
            msgKey (str): 消息模板key.
            openConversationId (str): 会话ID.
            robotCode (str): 机器人编码.
            coolAppCode (str): 酷应用编码.
        """
        url = "https://api.dingtalk.com/v1.0/robot/privateChatMessages/send"
        data = {
            "msgParam": msgParam,
            "msgKey": msgKey,
            "openConversationId": openConversationId,
            "robotCode": robotCode,
            "coolAppCode": coolAppCode
        }
        return await self.post_new(url, json=data)


    async def update_group_admins(self, open_conversation_id: str, user_ids: list, role: int) -> str:
        """
        更新群管理员。

        args:
            open_conversation_id (str): 群ID。
            user_ids (list): 用户userid列表，最多12个。
            role (int): 群成员类型，2表示群管理员，3表示普通群成员。
        """
        url = "https://api.dingtalk.com/v1.0/im/sceneGroups/subAdmins"
        data = {
            "openConversationId": open_conversation_id,
            "userIds": user_ids,
            "role": role
        }
        return await self.put_new(url, json=data)


    async def update_group_member_nick(self, open_conversation_id: str, user_id: str, group_nick: str) -> str:
        """
        更新群成员的群昵称.

        args:
            open_conversation_id (str): 群ID。
            user_id (str): 用户的userid。
            group_nick (str): 用户群昵称，最长不超过30字符，建议长度在10字符以内。
        """
        url = "https://api.dingtalk.com/v1.0/im/sceneGroups/members/groupNicks"
        data = {
            "openConversationId": open_conversation_id,
            "userId": user_id,
            "groupNick": group_nick
        }
        return await self.put_new(url, json=data)


    async def update_work_notification_status_bar(self, agent_id: int, task_id: int, status_value: str, status_bg: str = None) -> str:
        """
        更新工作通知状态栏.

        args:
            agent_id (int): 发送消息时使用的微应用的AgentID。
            task_id (int): 工作通知任务ID。
            status_value (str): 状态栏值。
            status_bg (str, optional): 状态栏背景色，推荐0xFF加六位颜色值。默认为None。
        """
        url = "https://oapi.dingtalk.com/topapi/message/corpconversation/status_bar/update"
        data = {
            "agent_id": agent_id,
            "task_id": task_id,
            "status_value": status_value,
            "status_bg": status_bg
        }
        return await self.post_old(url, json=data)

    def list_tools(self) -> list[types.Tool]:
        """
        List all available tools.
        """
        return [
            types.Tool(
                name="add_group_members",
                description="新增群成员。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "open_conversation_id": {
                            "type": "string",
                            "description": "群ID。企业内部应用和第三方企业应用通过调用创建群接口获取。",
                        },
                        "user_ids": {
                            "type": "string",
                            "description": "批量增加的成员userid，多个userid之间使用英文逗号分隔，最多传100个。",
                        },
                    },
                    "required": ["open_conversation_id", "user_ids"],
                },
            ),

            types.Tool(
                name="send_work_notification",
                description="调用本接口发送工作通知消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "integer",
                            "description": "发送消息时使用的微应用的AgentID。企业内部应用可在开发者后台的应用详情页面查看；第三方企业应用可调用获取企业授权信息接口获取。",
                        },
                        "userid_list": {
                            "type": "string",
                            "description": "接收者的userid列表，最大用户列表长度100。与dept_id_list和to_all_user互斥，必须指定其中之一。",
                        },
                        "dept_id_list": {
                            "type": "string",
                            "description": "接收者的部门id列表，最大列表长度20。接收者是部门ID时，包括子部门下的所有用户。与userid_list和to_all_user互斥，必须指定其中之一。",
                        },
                        "to_all_user": {
                            "type": "boolean",
                            "description": "是否发送给企业全部用户。当设置为false时必须指定userid_list或dept_id_list其中一个参数的值。",
                        },
                        "msg": {
                            "type": "object",
                            "description": "消息内容，最长不超过2048个字节，支持多种工作通知类型（如文本、图片、语音等）。具体格式参考官方文档。",
                            "properties": {
                                "msgtype": {
                                    "type": "string",
                                    "description": "消息类型，例如：text、image、voice等。",
                                },
                                "text": {
                                    "type": "object",
                                    "description": "当msgtype为text时的消息内容。",
                                    "properties": {
                                        "content": {
                                            "type": "string",
                                            "description": "文本消息的内容。",
                                        }
                                    }
                                }
                            },
                            "required": ["msgtype"],
                        }
                    },
                    "required": ["agent_id", "msg"],
                },
            )
            ,
            types.Tool(
                name="batch_recall_robot_messages",
                description="批量撤回人与机器人会话中机器人消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，需要与批量发送人与机器人会话中机器人消息接口中使用的robotCode保持一致。",
                        },
                        "processQueryKeys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "消息唯一标识列表，可通过批量发送人与机器人会话中机器人消息接口获取。每次最多传20个；在发送消息24小时内可以通过processQueryKey撤回消息，超过24小时则无法撤回消息。",
                        },
                    },
                    "required": ["robotCode", "processQueryKeys"],
                },
            ),
            types.Tool(
                name="batch_set_group_administrators",
                description="批量设置企业群内用户为管理员身份或取消管理员身份。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "开放群ID。可以通过调用创建群会话接口获取。",
                        },
                        "userIds": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "企业员工userid列表。可以通过调用获取部门用户userid列表接口获取。",
                        },
                        "role": {
                            "type": "integer",
                            "description": "设置类型，取值：2（添加为管理员）或 3（删除该管理员）。",
                        },
                    },
                    "required": ["openConversationId", "userIds", "role"],
                },
            ),
            types.Tool(
                name="batch_recall_robot_messages",
                description="调用本接口批量撤回人与人会话中机器人消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "会话ID，需要与人与人会话中机器人发送普通消息接口或人与人会话中机器人发送互动卡片接口使用的openConversationId保持一致。",
                        },
                        "robotCode": {
                            "type": "string",
                            "description": "机器人编码，需要与人与人会话中机器人发送普通消息接口或人与人会话中机器人发送互动卡片接口使用的robotCode保持一致。",
                        },
                        "processQueryKeys": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "消息id。企业内部应用，可通过人与人会话中机器人发送互动卡片接口或人与人会话中机器人发送普通消息接口，获取processQueryKey参数值。",
                        },
                    },
                    "required": ["openConversationId", "robotCode", "processQueryKeys"],
                },
            ),
            types.Tool(
                name="batch_query_robot_message_read_status",
                description="批量查询人与机器人会话中机器人消息是否已读。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，详情参考机器人 ID。",
                        },
                        "processQueryKey": {
                            "type": "string",
                            "description": "消息唯一标识，可通过批量发送人与机器人会话中机器人消息接口返回参数中 processQueryKey 字段获取。注意：在发送消息24小时内可以通过 processQueryKey 查询消息已读状态，超过24小时则无法查询。",
                        },
                    },
                    "required": ["robotCode", "processQueryKey"],
                },
            ),
            types.Tool(
                name="query_group_message_read_status",
                description="查询企业机器人群聊消息用户已读状态。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID，需要与机器人发送群聊消息接口时使用的openConversationId一致。可选参数。",
                        },
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，需要与机器人发送群聊消息接口时使用的robotCode一致。可选参数。",
                        },
                        "processQueryKey": {
                            "type": "string",
                            "description": "消息唯一标识。必填参数。",
                        },
                        "maxResults": {
                            "type": "integer",
                            "description": "分页查询每页的数量，最大值200。可选参数。",
                        },
                        "nextToken": {
                            "type": "string",
                            "description": "分页游标，置空表示从首页开始查询。可选参数。",
                        },
                    },
                    "required": ["processQueryKey"],
                },
            ),
            types.Tool(
                name="batch_send_robot_messages",
                description="调用本接口批量发送人与机器人会话（人与机器人单聊）中机器人消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，本接口只支持企业内部应用机器人调用，该参数使用企业内部应用机器人的robotCode。",
                        },
                        "userIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "接收机器人消息的用户的userId列表。每次最多传20个。",
                        },
                        "msgKey": {
                            "type": "string",
                            "description": "消息模板key，详情参考企业机器人发送消息的消息类型。",
                        },
                        "msgParam": {
                            "type": "string",
                            "description": "消息模板参数，详情参考企业机器人发送消息的消息类型。",
                        },
                    },
                    "required": ["robotCode", "userIds", "msgKey", "msgParam"],
                },
            ),
            types.Tool(
                name="clear_robot_shortcut",
                description="清空单聊机器人快捷入口。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，参见机器人名词表-robotCode内容，获取robotCode。",
                        },
                    },
                    "required": ["robotCode"],
                },
            ),
            types.Tool(
                name="close_interactive_card_header",
                description="调用本接口关闭会话中的互动卡片吊顶。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "outTrackId": {
                            "type": "string",
                            "description": "唯一标识一张卡片的外部ID，最大长度64。调用者自己定义的卡片唯一标识。",
                        },
                        "conversationType": {
                            "type": "integer",
                            "description": "会话类型：1-群聊，2-单聊助手。",
                        },
                        "openConversationId": {
                            "type": "string",
                            "description": "会话ID。群聊时必传，基于群模板创建的群或安装群聊酷应用的群需要提供；单聊助手不传此参数。",
                        },
                        "userId": {
                            "type": "string",
                            "description": "用户userId。当会话类型为单聊助手时，userId和unionId二选一必填；其他会话类型不需要传入。",
                        },
                        "unionId": {
                            "type": "string",
                            "description": "用户unionId。当会话类型为单聊助手时，userId和unionId二选一必填；其他会话类型不需要传入。",
                        },
                        "robotCode": {
                            "type": "string",
                            "description": "机器人编码。单聊助手时必填，传入企业内部开发-机器人应用的AppKey值、企业内部应用机器人或第三方企业应用机器人的编码；其他会话类型不需要传入。",
                        },
                        "coolAppCode": {
                            "type": "string",
                            "description": "酷应用编码。基于群模板创建的群不需要传入；安装群聊酷应用的群必须传入；单聊助手不需要传入。",
                        },
                        "groupTemplateId": {
                            "type": "string",
                            "description": "群模板ID。基于群模板创建的群必须传入；安装群聊酷应用的群不需要传入；其他会话类型不需要传入。",
                        },
                    },
                    "required": ["outTrackId", "conversationType"],
                },
            ),
            types.Tool(
                name="create_group",
                description="根据群模板ID创建群。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "群名称。最长不超过30字符，建议长度在10字符以内。",
                        },
                        "template_id": {
                            "type": "string",
                            "description": "群模板ID，登录开发者后台 > 开放能力 > 场景群 > 群模板查看id。",
                        },
                        "owner_user_id": {
                            "type": "string",
                            "description": "群主的userid。",
                        },
                        "user_ids": {
                            "type": "string",
                            "description": "群成员userid列表，最多传999个。",
                        },
                        "subadmin_ids": {
                            "type": "string",
                            "description": "群管理员userid列表。",
                        },
                        "uuid": {
                            "type": "string",
                            "description": "建群去重的业务ID，由接口调用方指定。建议长度在64字符以内。",
                        },
                        "icon": {
                            "type": "string",
                            "description": "群头像，格式为mediaId。需要调用上传媒体文件接口上传群头像，获取mediaId。",
                        },
                        "mention_all_authority": {
                            "type": "number",
                            "description": "@all 权限：0（默认）：所有人都可以@all；1：仅群主可@all。",
                        },
                        "show_history_type": {
                            "type": "number",
                            "description": "新成员是否可查看聊天历史消息：0（默认）：不可以查看历史记录；1：可以查看历史记录。",
                        },
                        "validation_type": {
                            "type": "number",
                            "description": "入群是否需要验证：0（默认）：不验证入群；1：入群验证。",
                        },
                        "searchable": {
                            "type": "number",
                            "description": "群是否可搜索：0（默认）：不可搜索；1：可搜索。",
                        },
                        "chat_banned_type": {
                            "type": "number",
                            "description": "是否开启群禁言：0（默认）：不禁言；1：全员禁言。",
                        },
                        "management_type": {
                            "type": "number",
                            "description": "管理类型：0（默认）：所有人可管理；1：仅群主可管理。",
                        },
                        "only_admin_can_ding": {
                            "type": "number",
                            "description": "群内发DING权限：0（默认）：所有人可发DING；1：仅群主和管理员可发DING。",
                        },
                        "all_members_can_create_mcs_conf": {
                            "type": "number",
                            "description": "群会议权限：0：仅群主和管理员可发起视频和语音会议；1（默认）：所有人可发起视频和语音会议。",
                        },
                        "all_members_can_create_calendar": {
                            "type": "number",
                            "description": "群日历设置项，群内非好友/同事的成员是否可相互发起钉钉日程：0（默认）：非好友/同事的成员不可发起钉钉日程；1：非好友/同事的成员可以发起钉钉日程。",
                        },
                        "group_email_disabled": {
                            "type": "number",
                            "description": "是否禁止发送群邮件：0（默认）：群内成员可以对本群发送群邮件；1：群内成员不可对本群发送群邮件。",
                        },
                        "only_admin_can_set_msg_top": {
                            "type": "number",
                            "description": "置顶群消息权限：0（默认）：所有人可置顶群消息；1：仅群主和管理员可置顶群消息。",
                        },
                        "add_friend_forbidden": {
                            "type": "number",
                            "description": "群成员私聊权限：0（默认）：所有人可私聊；1：普通群成员之间不能够加好友、单聊，且部分功能使用受限（管理员与非管理员之间不受影响）。",
                        },
                        "group_live_switch": {
                            "type": "number",
                            "description": "群直播权限：0：仅群主与管理员可发起直播；1（默认）：群内任意成员可发起群直播。",
                        },
                        "members_to_admin_chat": {
                            "type": "number",
                            "description": "是否禁止非管理员向管理员发起单聊：0（默认）：非管理员可以向管理员发起单聊；1：禁止非管理员向管理员发起单聊。",
                        },
                    },
                    "required": ["title", "template_id", "owner_user_id"],
                },
            ),
            types.Tool(
                name="create_and_open_interactive_card",
                description="创建并开启会话中的互动卡片吊顶。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cardTemplateId": {
                            "type": "string",
                            "description": "互动卡片的消息模板ID。企业内部应用和第三方企业应用需分别调用对应接口获取模板ID。",
                        },
                        "outTrackId": {
                            "type": "string",
                            "description": "唯一标识一张卡片的外部ID，最大长度64。调用者需保存此值以用于关闭互动卡片吊顶。",
                        },
                        "callbackRouteKey": {
                            "type": "string",
                            "description": "可控制卡片回调时的路由Key，用于指定特定的callbackUrl。企业内部应用和第三方企业应用需分别调用对应接口获取参数。",
                        },
                        "cardData": {
                            "type": "object",
                            "description": "卡片数据。",
                            "properties": {
                                "cardParamMap": {
                                    "type": "object",
                                    "description": "卡片模板内容替换参数。普通文本类型为key-value对，多媒体类型需传入media_id。",
                                    "additionalProperties": {
                                        "type": "string"
                                    }
                                }
                            },
                            "required": ["cardParamMap"]
                        },
                        "userIdPrivateDataMap": {
                            "type": "object",
                            "description": "卡片模板userId差异用户参数。key为用户userId，value为卡片数据。",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "cardParamMap": {
                                        "type": "object",
                                        "description": "卡片模板内容替换参数。",
                                        "additionalProperties": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "required": ["cardParamMap"]
                            }
                        },
                        "unionIdPrivateDataMap": {
                            "type": "object",
                            "description": "卡片模板unionId差异用户参数。key为用户unionId，value为卡片数据。",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "cardParamMap": {
                                        "type": "object",
                                        "description": "卡片模板内容替换参数。",
                                        "additionalProperties": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "required": ["cardParamMap"]
                            }
                        },
                        "cardSettings": {
                            "type": "object",
                            "description": "卡片设置项。",
                            "properties": {
                                "pullStrategy": {
                                    "type": "boolean",
                                    "description": "是否开启卡片纯拉模式。true表示开启，false表示关闭。",
                                }
                            }
                        },
                        "conversationType": {
                            "type": "integer",
                            "description": "会话类型。1表示群聊，2表示单聊助手。",
                        },
                        "openConversationId": {
                            "type": "string",
                            "description": "会话ID。群聊时必传，单聊助手时不传。",
                        },
                        "userId": {
                            "type": "string",
                            "description": "用户userId。当会话类型为单聊助手时，userId和unionId二选一必填。",
                        },
                        "unionId": {
                            "type": "string",
                            "description": "用户unionId。当会话类型为单聊助手时，userId和unionId二选一必填。",
                        },
                        "robotCode": {
                            "type": "string",
                            "description": "机器人编码。单聊助手时必填，其他会话类型不需传入。",
                        },
                        "coolAppCode": {
                            "type": "string",
                            "description": "酷应用编码。安装群聊酷应用的群时必传，其他情况不需传入。",
                        },
                        "groupTemplateId": {
                            "type": "string",
                            "description": "群模板ID。基于群模板创建的群时必传，其他情况不需传入。",
                        },
                        "receiverUserIdList": {
                            "type": "array",
                            "description": "吊顶可见者userId列表，最多可传100个userId。若不传，则默认吊顶对会话内所有人可见。",
                            "items": {
                                "type": "string"
                            }
                        },
                        "receiverUnionIdList": {
                            "type": "array",
                            "description": "吊顶可见者unionId列表，最多可传100个unionId。若不传，则默认吊顶对会话内所有人可见。",
                            "items": {
                                "type": "string"
                            }
                        },
                        "expiredTime": {
                            "type": "integer",
                            "description": "吊顶的过期时间，毫秒级时间戳。不传入时，默认不过期。",
                        },
                        "platforms": {
                            "type": "string",
                            "description": "期望吊顶的端，多个值用“|”分隔。例如：ios|mac|android|win。",
                        }
                    },
                    "required": ["cardTemplateId", "outTrackId", "cardData", "conversationType"],
                },
            ),
            types.Tool(
                name="create_group",
                description="创建内部群会话。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "群名称，长度限制为1~20个字符。",
                        },
                        "owner": {
                            "type": "string",
                            "description": "群主的userId，可通过根据手机号查询用户接口获取userid参数值。该员工必须为会话useridlist的成员之一。",
                        },
                        "useridlist": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "群成员列表，每次最多支持40人，群人数上限为1000。可通过根据手机号查询用户接口获取userid参数值。",
                        },
                        "showHistoryType": {
                            "type": "number",
                            "description": "新成员是否可查看100条历史消息：1-可查看；0（默认）-不可查看。",
                        },
                        "searchable": {
                            "type": "number",
                            "description": "群是否可以被搜索：0（默认）-不可搜索；1-可搜索。",
                        },
                        "validationType": {
                            "type": "number",
                            "description": "入群是否需要验证：0（默认）-不验证；1-入群验证。",
                        },
                        "mentionAllAuthority": {
                            "type": "number",
                            "description": "@all 使用范围：0（默认）-所有人可使用；1-仅群主可@all。",
                        },
                        "managementType": {
                            "type": "number",
                            "description": "群管理类型：0（默认）-所有人可管理；1-仅群主可管理。",
                        },
                        "chatBannedType": {
                            "type": "number",
                            "description": "是否开启群禁言：0（默认）-不禁言；1-全员禁言。",
                        },
                    },
                    "required": ["name", "owner", "useridlist"],
                },
            ),

            types.Tool(
                name="deactivate_group_template",
                description="根据群模板ID停用群模板。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner_user_id": {
                            "type": "string",
                            "description": "群主userid。",
                        },
                        "template_id": {
                            "type": "string",
                            "description": "群模板id，登录开发者后台 > 开放能力 > 场景群 > 群模板查看id。",
                        },
                        "open_conversation_id": {
                            "type": "string",
                            "description": "群ID。企业内部应用或第三方企业应用通过调用创建群接口获取open_conversation_id参数值。",
                        },
                    },
                    "required": ["owner_user_id", "template_id", "open_conversation_id"],
                },
            )
            ,

            types.Tool(
                name="download_robot_message_file",
                description="调用本接口下载机器人接收消息的文件内容。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "downloadCode": {
                            "type": "string",
                            "description": "用户向机器人发送文件消息后，机器人回调给开发者消息中的下载码。",
                        },
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码。",
                        },
                    },
                    "required": ["downloadCode", "robotCode"],
                },
            )
            ,
            types.Tool(
                name="apply_group_template",
                description="根据群模板ID启用群模板。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner_user_id": {
                            "type": "string",
                            "description": "群主的userid。",
                        },
                        "template_id": {
                            "type": "string",
                            "description": "群模板id，登录开发者后台 > 开放能力 > 场景群 > 群模板查看id。",
                        },
                        "open_conversation_id": {
                            "type": "string",
                            "description": "群ID。企业内部应用和第三方企业应用可通过调用创建群接口获取。",
                        },
                    },
                    "required": ["owner_user_id", "template_id", "open_conversation_id"],
                },
            ),
            types.Tool(
                name="recall_group_message",
                description="企业机器人撤回内部群消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID，需要与机器人发送群聊消息接口时使用的openConversationId一致。",
                        },
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，需要与机器人发送群聊消息接口时使用的robotCode一致。",
                        },
                        "processQueryKeys": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "消息ID列表。企业内部应用和第三方企业应用，通过机器人发送群聊消息接口返回参数processQueryKey字段中获取。",
                        },
                    },
                    "required": ["openConversationId", "robotCode", "processQueryKeys"],
                },
            ),

            types.Tool(
                name="get_work_notification_send_result",
                description="查询工作通知消息的发送结果。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "number",
                            "description": "发送消息时使用的微应用的AgentID。企业内部应用可在开发者后台的应用详情页面查看；第三方企业应用可通过获取企业授权信息接口获取。",
                        },
                        "task_id": {
                            "type": "number",
                            "description": "发送消息时钉钉返回的任务ID。可通过发送工作通知接口获取。仅支持查询24小时内的任务。",
                        },
                    },
                    "required": ["agent_id", "task_id"],
                },
            )
            ,
            types.Tool(
                name="update_group",
                description="调用本接口更新群会话。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chatid": {
                            "type": "string",
                            "description": "群会话ID。仅支持通过调用服务端创建群接口获取的chatid参数值，不支持通过调用前端JSAPI获取的chatid。",
                        },
                        "name": {
                            "type": "string",
                            "description": "群名称，长度限制为1~20个字符。可选参数。",
                        },
                        "owner": {
                            "type": "string",
                            "description": "群主的userId，可通过根据手机号查询用户接口获取userId。该员工必须为会话useridlist的成员之一。可选参数。",
                        },
                        "ownerType": {
                            "type": "string",
                            "description": "群主类型。可选参数。emp：企业员工；ext：外部联系人。",
                        },
                        "add_useridlist": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "添加的群成员列表，每次最多支持40人，群人数上限为1000。可通过根据手机号查询用户接口获取userId。可选参数。",
                        },
                        "del_useridlist": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "删除的成员列表，可通过根据手机号查询用户接口获取userId。可选参数。",
                        },
                        "add_extidlist": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "添加的外部联系人成员列表。可选参数。",
                        },
                        "del_extidlist": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "删除的外部联系人成员列表。可选参数。",
                        },
                        "icon": {
                            "type": "string",
                            "description": "群头像的mediaId，可通过上传媒体文件接口获取media_id参数值。可选参数。",
                        },
                        "searchable": {
                            "type": "number",
                            "description": "群是否可以被搜索。0（默认）：不可搜索；1：可搜索。可选参数。",
                        },
                        "validationType": {
                            "type": "number",
                            "description": "入群是否需要验证。0（默认）：不验证；1：入群验证。可选参数。",
                        },
                        "mentionAllAuthority": {
                            "type": "number",
                            "description": "@all 使用范围。0（默认）：所有人可使用；1：仅群主可@all。可选参数。",
                        },
                        "managementType": {
                            "type": "number",
                            "description": "群管理类型。0（默认）：所有人可管理；1：仅群主可管理。可选参数。",
                        },
                        "chatBannedType": {
                            "type": "number",
                            "description": "是否开启群禁言。0（默认）：不禁言；1：全员禁言。可选参数。",
                        },
                        "showHistoryType": {
                            "type": "number",
                            "description": "新成员是否可查看100条历史消息。1：可查看；0（默认）：不可查看。如果不传值，代表不可查看。可选参数。",
                        },
                        "isBan": {
                            "type": "boolean",
                            "description": "是否禁言。true：禁言；false：不禁言。可选参数。",
                        },
                    },
                    "required": ["chatid"],
                },
            ),
            types.Tool(
                name="recall_work_notification",
                description="撤回工作通知消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "number",
                            "description": "发送消息时使用的微应用的AgentID。",
                        },
                        "msg_task_id": {
                            "type": "number",
                            "description": "发送消息时钉钉返回的任务ID。仅支持撤回24小时内的工作消息通知。",
                        },
                    },
                    "required": ["agent_id", "msg_task_id"],
                },
            ),

            types.Tool(
                name="get_chat_info",
                description="调用本接口获取群设置和成员信息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chatid": {
                            "type": "string",
                            "description": "群会话的ID。仅支持通过调用服务端创建群接口获取的chatid参数值，不支持通过调用前端JSAPI获取的chatid。",
                        },
                    },
                    "required": ["chatid"],
                },
            )
            ,
            types.Tool(
                name="get_group_qrcode_link",
                description="调用本接口，获取群入群二维码邀请链接。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chatid": {
                            "type": "string",
                            "description": "群会话的chatid，可调用创建群接口获取chatid参数值。",
                        },
                        "userid": {
                            "type": "string",
                            "description": "分享二维码用户的userId。",
                        },
                    },
                    "required": ["chatid", "userid"],
                },
            ),
            types.Tool(
                name="get_open_conversation_id",
                description="通过chatId查询OpenConversationId。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chatId": {
                            "type": "string",
                            "description": "群会话chatId。企业内部应用可通过服务端创建群会话接口或客户端选择会话获取chatId参数值。",
                        },
                    },
                    "required": ["chatId"],
                },
            ),

            types.Tool(
                name="get_bot_list_in_group",
                description="调用本接口获取群内机器人列表。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID：基于群模板创建的群。调用创建群接口获取open_conversation_id参数值。",
                        },
                    },
                    "required": ["openConversationId"],
                },
            )
            ,
            types.Tool(
                name="get_message_send_progress",
                description="获取工作通知消息的发送进度。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "number",
                            "description": "发送消息时使用的微应用的AgentID。企业内部应用可在开发者后台的应用详情页面查看；第三方企业应用可通过调用获取企业授权信息接口获取。",
                        },
                        "task_id": {
                            "type": "number",
                            "description": "发送消息时钉钉返回的任务ID。可通过调用发送工作通知接口获取。仅支持查询24小时内的任务。",
                        },
                    },
                    "required": ["agent_id", "task_id"],
                },
            ),

            types.Tool(
                name="get_group_info",
                description="根据群ID查询群的信息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "open_conversation_id": {
                            "type": "string",
                            "description": "群ID。可以通过创建群接口获取。",
                        },
                    },
                    "required": ["open_conversation_id"],
                },
            )
            ,

            types.Tool(
                name="query_group_summary_info",
                description="根据群ID查询群的简要信息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID：\n"
                                        "- 基于群模板创建的群：\n"
                                        "  - 企业内部应用，调用创建群接口获取`open_conversation_id`参数值。\n"
                                        "  - 第三方企业应用，调用创建群接口获取`open_conversation_id`参数值。\n"
                                        "- 安装群聊酷应用的群：\n"
                                        "  - 企业内部应用，通过群内安装酷应用事件获取回调参数`OpenConversationId`参数值。",
                        },
                        "coolAppCode": {
                            "type": "string",
                            "description": "群聊酷应用编码：\n"
                                        "- 基于群模板创建的群：不需要传入此参数。\n"
                                        "- 安装群聊酷应用的群，必须传入此参数。",
                        },
                    },
                    "required": ["openConversationId"],
                },
            )
            ,

            types.Tool(
                name="batch_query_group_members",
                description="查询群成员信息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID：\n"
                                        "- 基于群模板创建的群：\n"
                                        "  - 企业内部应用，调用创建群接口获取`open_conversation_id`参数值。\n"
                                        "  - 第三方企业应用，调用创建群接口获取`open_conversation_id`参数值。\n"
                                        "- 安装群聊酷应用的群：\n"
                                        "  - 企业内部应用，通过群内安装酷应用事件获取回调参数`OpenConversationId`参数值。",
                        },
                        "coolAppCode": {
                            "type": "string",
                            "description": "群聊酷应用编码：\n"
                                        "- 基于群模板创建的群，不需要传入此参数。\n"
                                        "- 安装群聊酷应用的群，必须传入此参数。",
                        },
                        "maxResults": {
                            "type": "integer",
                            "description": "分页大小。\n"
                                        "说明：接口返回结果可能会大于或小于maxResults，以实际返回结果为准。如果群成员数量不超过1000，则直接一次性返回全部群成员；如果群成员数量大于1000，则按照分页大小分批次返回。",
                        },
                        "nextToken": {
                            "type": "string",
                            "description": "分页游标，置空表示从首页开始查询。",
                        },
                    },
                    "required": ["openConversationId", "maxResults"],
                },
            )
            ,
            types.Tool(
                name="get_group_mute_status",
                description="通过本接口查询群和群内成员的禁言状态。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "userId": {
                            "type": "string",
                            "description": "群成员userId。",
                        },
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID，通过创建群接口获取open_conversation_id字段值。",
                        },
                    },
                    "required": ["userId", "openConversationId"],
                },
            ),

            types.Tool(
                name="query_robot_message_read_list",
                description="查询人与人会话中机器人消息已读列表。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "人与人单聊开放会话ID。企业内部应用或第三方企业应用可通过相关接口获取。",
                        },
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，详情参考机器人 ID。",
                        },
                        "processQueryKey": {
                            "type": "string",
                            "description": "消息id。可通过人与人会话中机器人发送互动卡片或普通消息接口获取。",
                        },
                        "maxResults": {
                            "type": "integer",
                            "description": "分页查询每页的数量。",
                        },
                        "nextToken": {
                            "type": "string",
                            "description": "一次查询后返回的加密的分页凭证，首次查询不填。",
                        },
                    },
                    "required": ["processQueryKey"],
                },
            )
            ,
            types.Tool(
                name="query_single_chat_robot_shortcut",
                description="调用本接口查询单聊机器人的快捷入口。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，参见机器人名词表-robotCode内容，获取robotCode。",
                        },
                    },
                    "required": ["robotCode"],
                },
            ),
            types.Tool(
                name="send_ding_message",
                description="使用企业内机器人发送DING消息，支持应用内DING、短信DING、电话DING。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "robotCode": {
                            "type": "string",
                            "description": "发DING消息的机器人ID。创建企业内部应用机器人后，获取机器人robotCode。",
                        },
                        "remindType": {
                            "type": "integer",
                            "description": "DING消息类型。1：应用内DING；2：短信DING；3：电话DING。",
                        },
                        "receiverUserIdList": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "接收人userId列表。应用内DING消息每次接收人不能超过200个；短信DING和电话DING每次接收人不能超过20个。",
                        },
                        "content": {
                            "type": "string",
                            "description": "DING消息内容。",
                        },
                    },
                    "required": ["robotCode", "remindType", "receiverUserIdList", "content"],
                },
            ),

            types.Tool(
                name="recall_ding_message",
                description="撤回使用企业机器人发送的DING消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "robotCode": {
                            "type": "string",
                            "description": "发送DING消息的机器人ID。需要撤销的DING消息，发送和撤回操作必须是同一个机器人。",
                        },
                        "openDingId": {
                            "type": "string",
                            "description": "需要被撤回的DING消息ID。可通过调用发送DING消息接口获取。",
                        },
                    },
                    "required": ["robotCode", "openDingId"],
                },
            )
            ,
            types.Tool(
                name="delete_group_members",
                description="调用本接口删除群成员。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "open_conversation_id": {
                            "type": "string",
                            "description": "群ID。企业内部应用和第三方企业应用可通过调用创建群接口获取。",
                        },
                        "user_ids": {
                            "type": "string",
                            "description": "批量删除的成员userid，多个userid之间使用英文逗号分隔，最多传100个。",
                        },
                    },
                    "required": ["open_conversation_id", "user_ids"],
                },
            ),
            types.Tool(
                name="update_group",
                description="根据群ID更新群信息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "open_conversation_id": {
                            "type": "string",
                            "description": "群ID。可通过创建群接口获取。",
                        },
                        "title": {
                            "type": "string",
                            "description": "群名称。最长不超过30字符，建议长度在10字符以内。",
                        },
                        "owner_user_id": {
                            "type": "string",
                            "description": "群主的userId。",
                        },
                        "icon": {
                            "type": "string",
                            "description": "群头像，格式为mediaId。可通过上传媒体文件接口获取。",
                        },
                        "mention_all_authority": {
                            "type": "number",
                            "description": "@all 权限：0（默认）：所有人可@all；1：仅群主可@all。",
                        },
                        "show_history_type": {
                            "type": "number",
                            "description": "新成员是否可查看聊天历史消息：0（默认）：不可以；1：可以。",
                        },
                        "validation_type": {
                            "type": "number",
                            "description": "入群验证：0（默认）：不需要验证；1：入群验证。",
                        },
                        "searchable": {
                            "type": "number",
                            "description": "群是否可搜索：0（默认）：不可搜索；1：可搜索。",
                        },
                        "chat_banned_type": {
                            "type": "number",
                            "description": "群是否开启禁言：0（默认）：不禁言；1：全员禁言。",
                        },
                        "management_type": {
                            "type": "number",
                            "description": "管理类型：0（默认）：所有人可管理；1：仅群主可管理。",
                        },
                        "only_admin_can_ding": {
                            "type": "number",
                            "description": "群内发DING权限：0（默认）：所有人可发DING；1：仅群主和管理员可发DING。",
                        },
                        "all_members_can_create_mcs_conf": {
                            "type": "number",
                            "description": "群会议权限：0：仅群主和管理员可发起视频和语音会议；1（默认）：所有人可发起视频和语音会议。",
                        },
                        "all_members_can_create_calendar": {
                            "type": "number",
                            "description": "群日历设置项：0（默认）：非好友/同事的成员不可发起钉钉日程；1：非好友/同事的成员可以发起钉钉日程。",
                        },
                        "group_email_disabled": {
                            "type": "number",
                            "description": "是否禁止发送群邮件：0（默认）：群内成员可以对本群发送群邮件；1：群内成员不可对本群发送群邮件。",
                        },
                        "only_admin_can_set_msg_top": {
                            "type": "number",
                            "description": "置顶群消息权限：0（默认）：所有人可置顶群消息；1：仅群主和管理员可置顶群消息。",
                        },
                        "add_friend_forbidden": {
                            "type": "number",
                            "description": "群成员私聊权限：0（默认）：所有人可私聊；1：普通群成员之间不能够加好友、单聊，且部分功能使用受限（管理员与非管理员之间不受影响）。",
                        },
                        "group_live_switch": {
                            "type": "number",
                            "description": "群直播权限：0：仅群主与管理员可发起直播；1（默认）：群内任意成员可发起群直播。",
                        },
                        "members_to_admin_chat": {
                            "type": "number",
                            "description": "是否禁止非管理员向管理员发起单聊：0（默认）：非管理员可以向管理员发起单聊；1：禁止非管理员向管理员发起单聊。",
                        },
                        "plugin_customize_verify": {
                            "type": "number",
                            "description": "自定义群插件是否需要群主和管理员审批：0（默认）：不需要审批；1：需要审批。",
                        },
                    },
                    "required": ["open_conversation_id"],
                },
            ),

            types.Tool(
                name="query_group_template_robots",
                description="调用本接口查询群内群模板机器人信息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码。登录开发者后台 > 开放能力 > 场景群 > 机器人查看id。",
                        },
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID。企业内部应用或第三方企业应用可通过调用创建群接口获取open_conversation_id参数值。",
                        },
                    },
                    "required": [],
                },
            )
            ,
            types.Tool(
                name="send_group_assistant_message",
                description="通过群模板定义的机器人向群内发送消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target_open_conversation_id": {
                            "type": "string",
                            "description": "群ID。企业内部应用和第三方企业应用可通过调用创建群接口获取open_conversation_id参数值。",
                        },
                        "msg_template_id": {
                            "type": "string",
                            "description": "消息模板ID，详情参见场景群通用消息模板。",
                        },
                        "msg_param_map": {
                            "type": "string",
                            "description": "消息模板内容替换参数，普通文本类型。取值为Json格式的字符串。",
                        },
                        "msg_media_id_param_map": {
                            "type": "string",
                            "description": "消息模板内容替换参数，多媒体类型。取值为Json格式的字符串。",
                        },
                        "receiver_user_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "消息接收人userId列表。不设置则消息对群内所有成员可见。",
                        },
                        "receiver_union_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "消息接收人unionId列表。不设置则消息对群内所有成员可见。",
                        },
                        "receiver_mobiles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "消息接收人手机号列表。不设置则消息对群内所有成员可见。",
                        },
                        "at_mobiles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "@人的手机号列表。一次调用最多支持50人。",
                        },
                        "at_users": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "@人的userid列表。一次调用最多支持50人。",
                        },
                        "is_at_all": {
                            "type": "boolean",
                            "description": "是否@所有人：true：是；false：否。",
                        },
                        "robot_code": {
                            "type": "string",
                            "description": "机器人编码。登录开发者后台 > 开放能力 > 场景群 > 机器人查看id。",
                        },
                    },
                    "required": [
                        "target_open_conversation_id",
                        "msg_template_id",
                        "robot_code",
                    ],
                },
            ),
            types.Tool(
                name="update_group_member_nickname",
                description="调用本接口更新群成员在群中的昵称。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "userid": {
                            "type": "string",
                            "description": "要更改群昵称的群成员userId，可通过获取群会话信息接口获取群成员userId。",
                        },
                        "chatid": {
                            "type": "string",
                            "description": "群会话ID，可通过创建群会话接口获取chatid参数值。",
                        },
                        "group_nick": {
                            "type": "string",
                            "description": "该成员在群中的昵称。",
                        },
                    },
                    "required": ["userid", "chatid", "group_nick"],
                },
            ),
            types.Tool(
                name="update_group_admin",
                description="调用本接口更新群管理员。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chatid": {
                            "type": "string",
                            "description": "群会话ID，可通过创建群接口获取chatid参数值。",
                        },
                        "userids": {
                            "type": "string",
                            "description": "群成员userId，可通过根据手机号查询用户接口获取userId参数值。",
                        },
                        "role": {
                            "type": "number",
                            "description": "角色类型。2：添加为管理员；3：删除该管理员。",
                        },
                    },
                    "required": ["chatid", "userids", "role"],
                },
            ),
            types.Tool(
                name="set_group_member_mute_status",
                description="设置场景群内的群成员禁言状态，可设置指定群成员禁言或解除禁言。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "userIdList": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "需要禁言或取消禁言的群成员userId列表。群主和群管理员无法被设置禁言，最多传999个。",
                        },
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID，通过创建群接口获取open_conversation_id参数值。",
                        },
                        "muteStatus": {
                            "type": "integer",
                            "description": "禁言状态：0表示取消禁言，1表示禁言。",
                        },
                        "muteDuration": {
                            "type": "integer",
                            "description": "禁言持续时长，单位：毫秒。",
                        },
                    },
                    "required": ["userIdList", "openConversationId", "muteStatus", "muteDuration"],
                },
            ),
            types.Tool(
                name="set_group_member_private_chat",
                description="设置群成员之间是否可以添加好友和私聊。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chatid": {
                            "type": "string",
                            "description": "企业会话ID。可以通过以下方式获取：\n- 调用服务端接口获取：\n  - 调用创建群接口获取chatid参数值。\n- 调用客户端API获取：\n  - 小程序，调用选择会话接口获取chatId参数值。\n  - H5微应用，调用根据corpId选择会话接口获取chatId参数值。",
                        },
                        "is_prohibit": {
                            "type": "boolean",
                            "description": "是否开启禁止开关。\n- true：开启禁止开关。\n- false：关闭禁止开关。",
                        },
                    },
                    "required": ["chatid", "is_prohibit"],
                },
            ),
            types.Tool(
                name="set_robot_shortcut",
                description="调用本接口设置单聊机器人的快捷入口。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，参见机器人名词表-robotCode内容，获取robotCode。可选参数。",
                        },
                        "pluginInfoList": {
                            "type": "array",
                            "description": "插件列表。可选参数。",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "pcUrl": {
                                        "type": "string",
                                        "description": "PC端会话快捷入口跳转链接。可选参数。",
                                    },
                                    "mobileUrl": {
                                        "type": "string",
                                        "description": "手机端快捷入口跳转链接。可选参数。",
                                    },
                                    "name": {
                                        "type": "object",
                                        "description": "快捷入口的名称，支持国际化形式，如{\"en_US\":\"test123\",\"zh_CN\":\"测试123\"}。必填参数。",
                                        "additionalProperties": {
                                            "type": "string"
                                        }
                                    },
                                    "icon": {
                                        "type": "string",
                                        "description": "快捷入口的图标id，可通过调用上传媒体文件接口获取参数字段mediaId。必填参数。",
                                    }
                                },
                                "required": ["name", "icon"],
                            },
                        },
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="send_group_message",
                description="通过应用机器人发送群聊消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "msgParam": {
                            "type": "string",
                            "description": "消息模板参数，详情参考企业机器人发送消息的消息类型。长度限制 15000 字节以内。",
                        },
                        "msgKey": {
                            "type": "string",
                            "description": "消息模板key，详情参考企业机器人发送消息的消息类型。",
                        },
                        "openConversationId": {
                            "type": "string",
                            "description": "会话ID：\n- 如果是企业内部群：\n  - 新创建企业内部群，企业内部应用，可调用创建企业内部群接口获取。\n  - 已存在的企业内部群，可调用chooseChat JSAPI获取。\n- 如果是场景群：\n  - 企业内部应用，可调用创建场景群接口获取或chooseChat选择会话JSAPI获取。\n  - 第三方企业应用，可调用创建场景群接口获取。",
                        },
                        "robotCode": {
                            "type": "string",
                            "description": "机器人的编码，详情参考机器人 ID。",
                        },
                        "coolAppCode": {
                            "type": "string",
                            "description": "群聊酷应用编码，详情参考群聊酷应用。当使用群聊酷应用的方式安装机器人时，必须传入此参数。",
                        },
                    },
                    "required": ["msgParam", "msgKey"],
                },
            ),
            types.Tool(
                name="send_private_chat_message",
                description="调用本接口实现人与人会话中机器人发送普通消息。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "msgParam": {
                            "type": "string",
                            "description": "消息模板参数，详情参考企业机器人发送消息的消息类型。",
                        },
                        "msgKey": {
                            "type": "string",
                            "description": "消息模板key，详情参考企业机器人发送消息的消息类型。",
                        },
                        "openConversationId": {
                            "type": "string",
                            "description": "会话ID。企业内部应用可通过批量安装酷应用到单聊会话或监听单聊酷应用事件获取OpenConversationId参数值；第三方企业应用可通过批量安装酷应用到单聊会话并监听单聊酷应用事件获取OpenConversationId参数值。",
                        },
                        "robotCode": {
                            "type": "string",
                            "description": "机器人编码，该参数使用企业机器人的robotCode。详情参考机器人 ID。",
                        },
                        "coolAppCode": {
                            "type": "string",
                            "description": "酷应用编码。",
                        },
                    },
                    "required": ["msgParam", "msgKey", "openConversationId", "robotCode", "coolAppCode"],
                },
            ),
            types.Tool(
                name="update_group_administrators",
                description="更新群的群管理员。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID。企业内部应用或第三方企业应用需调用创建群接口获取open_conversation_id参数值。",
                        },
                        "userIds": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "用户userid列表，最多传12个。",
                        },
                        "role": {
                            "type": "integer",
                            "description": "群成员类型：2表示群管理员，3表示普通群成员。",
                        },
                    },
                    "required": ["openConversationId", "userIds", "role"],
                },
            ),

            types.Tool(
                name="update_group_member_nick",
                description="调用本接口更新场景群群成员的群昵称。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "openConversationId": {
                            "type": "string",
                            "description": "群ID。企业内部应用或第三方企业应用，调用创建群接口获取open_conversation_id参数值。",
                        },
                        "userId": {
                            "type": "string",
                            "description": "用户的userid。",
                        },
                        "groupNick": {
                            "type": "string",
                            "description": "用户群昵称。最长不超过30字符，建议长度在10字符以内。",
                        },
                    },
                    "required": ["openConversationId", "userId", "groupNick"],
                },
            )
            ,
            types.Tool(
                name="update_work_notification_status_bar",
                description="调用本接口，更新 OA 工作通知消息的状态。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "number",
                            "description": "发送消息时使用的微应用的AgentID。企业内部应用可在开发者后台的应用详情页面查看；第三方企业应用通过获取企业授权信息接口获取。",
                        },
                        "task_id": {
                            "type": "number",
                            "description": "工作通知任务ID。通过发送工作通知接口获取。",
                        },
                        "status_value": {
                            "type": "string",
                            "description": "状态栏值。",
                        },
                        "status_bg": {
                            "type": "string",
                            "description": "状态栏背景色，推荐0xFF加六位颜色值。可选参数。",
                        },
                    },
                    "required": ["agent_id", "task_id", "status_value"],
                },
            ),
        ]

async def serve():
    _mcp_server = MCPServer(name="DingtalkIMServer")
    dingtalk_server = DingtalkIMServer()

    @_mcp_server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return dingtalk_server.list_tools()
    
    @_mcp_server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None = None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        try:
            match name:
                case 'add_group_members_old': 
                        result = await dingtalk_server.add_group_members_old(**arguments)
                case 'batch_query_group_members': 
                        result = await dingtalk_server.batch_query_group_members(**arguments)
                case 'batch_recall_robot_messages': 
                        result = await dingtalk_server.batch_recall_robot_messages(**arguments)
                case 'batch_send_robot_messages': 
                        result = await dingtalk_server.batch_send_robot_messages(**arguments)
                case 'cleanup': 
                        result = await dingtalk_server.cleanup(**arguments)
                case 'clear_robot_shortcut': 
                        result = await dingtalk_server.clear_robot_shortcut(**arguments)
                case 'close_group_template': 
                        result = await dingtalk_server.close_group_template(**arguments)
                case 'close_interactive_card_top_box': 
                        result = await dingtalk_server.close_interactive_card_top_box(**arguments)
                case 'create_and_open_interactive_card':
                        result = await dingtalk_server.create_and_open_interactive_card(**arguments)
                case 'create_group':
                        result = await dingtalk_server.create_group(**arguments)
                case 'delete_group_members':
                        result = await dingtalk_server.delete_group_members(**arguments)
                case 'download_robot_message_file':
                        result = await dingtalk_server.download_robot_message_file(**arguments)
                case 'enable_group_template':
                        result = await dingtalk_server.enable_group_template(**arguments)
                case 'ensure_session':
                        result = await dingtalk_server.ensure_session(**arguments)
                case 'get_access_token':
                        result = await dingtalk_server.get_access_token(**arguments)
                case 'get_bot_list_in_group':
                        result = await dingtalk_server.get_bot_list_in_group(**arguments)
                case 'get_chat_info':
                        result = await dingtalk_server.get_chat_info(**arguments)
                case 'get_group_info':
                        result = await dingtalk_server.get_group_info(**arguments)
                case 'get_group_mute_status':
                        result = await dingtalk_server.get_group_mute_status(**arguments)
                case 'get_group_qrcode':
                        result = await dingtalk_server.get_group_qrcode(**arguments)
                case 'get_group_template_robots':
                        result = await dingtalk_server.get_group_template_robots(**arguments)
                case 'get_message_read_status':
                        result = await dingtalk_server.get_message_read_status(**arguments)
                case 'get_new':
                        result = await dingtalk_server.get_new(**arguments)
                case 'get_old':
                        result = await dingtalk_server.get_old(**arguments)
                case 'get_open_conversation_id':
                        result = await dingtalk_server.get_open_conversation_id(**arguments)
                case 'get_send_progress':
                        result = await dingtalk_server.get_send_progress(**arguments)
                case 'get_work_notification_send_result':
                        result = await dingtalk_server.get_work_notification_send_result(**arguments)
                case 'post_new':
                        result = await dingtalk_server.post_new(**arguments)
                case 'post_old':
                        result = await dingtalk_server.post_old(**arguments)
                case 'query_group_message_read_status':
                        result = await dingtalk_server.query_group_message_read_status(**arguments)
                case 'query_group_summary':
                        result = await dingtalk_server.query_group_summary(**arguments)
                case 'query_robot_message_read_list':
                        result = await dingtalk_server.query_robot_message_read_list(**arguments)
                case 'query_robot_plugin_shortcut':
                        result = await dingtalk_server.query_robot_plugin_shortcut(**arguments)
                case 'recall_ding_message':
                        result = await dingtalk_server.recall_ding_message(**arguments)
                case 'recall_group_message':
                        result = await dingtalk_server.recall_group_message(**arguments)
                case 'recall_work_notification':
                        result = await dingtalk_server.recall_work_notification(**arguments)
                case 'send_ding_message':
                        result = await dingtalk_server.send_ding_message(**arguments)
                case 'send_group_assistant_message_old':
                        result = await dingtalk_server.send_group_assistant_message_old(**arguments)
                case 'send_group_message':
                        result = await dingtalk_server.send_group_message(**arguments)
                case 'send_private_chat_message':
                        result = await dingtalk_server.send_private_chat_message(**arguments)
                case 'send_work_notification_old':
                        result = await dingtalk_server.send_work_notification_old(**arguments)
                case 'set_group_administrators':
                        result = await dingtalk_server.set_group_administrators(**arguments)
                case 'set_group_member_mute_status':
                        result = await dingtalk_server.set_group_member_mute_status(**arguments)
                case 'set_group_member_private_chat':
                        result = await dingtalk_server.set_group_member_private_chat(**arguments)
                case 'set_robot_plugin':
                        result = await dingtalk_server.set_robot_plugin(**arguments)
                case 'update_group':
                        result = await dingtalk_server.update_group(**arguments)
                case 'update_group_admin_old':
                        result = await dingtalk_server.update_group_admin_old(**arguments)
                case 'update_group_admins':
                        result = await dingtalk_server.update_group_admins(**arguments)
                case 'update_group_chat_old':
                        result = await dingtalk_server.update_group_chat_old(**arguments)
                case 'update_group_member_nick':
                        result = await dingtalk_server.update_group_member_nick(**arguments)
                case 'update_group_nick':
                        result = await dingtalk_server.update_group_nick(**arguments)
                case 'update_work_notification_status_bar':
                        result = await dingtalk_server.update_work_notification_status_bar(**arguments)
            return [types.TextContent(type="text", text=str(result))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
        
    async with stdio_server() as (read_stream, write_stream):
        try:
            await _mcp_server.run(
                read_stream,
                write_stream,
                _mcp_server.create_initialization_options(),
            )
        except Exception as e:
            raise
        finally:
            await dingtalk_server.cleanup()
    
class ServerWrapper():
    """A wrapper to compat with mcp[cli]"""
    def run(self):
        asyncio.run(serve())

server = ServerWrapper()

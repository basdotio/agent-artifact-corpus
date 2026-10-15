from typing import Any
import httpx
import re
import time
import logging
from .crypto import aes_ecb_decrypt
from .logger import get_logger


logger = get_logger(__name__)


async def get_courses(JSESSIONID: str) -> dict[str, str]:
    cookies = {
        "JSESSIONID": JSESSIONID,
    }

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Referer": "http://112.5.88.114:31101/yiban-web/stu/homePage.jhtml",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(
            "http://112.5.88.114:31101/yiban-web/stu/toCourse.jhtml",
            cookies=cookies,
            headers=headers,
        )

    if response.status_code != 200:
        logger.error("Failed to fetch courses, status code: %s", response.status_code)
        raise Exception("Failed to fetch courses")

    pattern = r'href="toSubject\.jhtml\?courseId=(\d+)".*?<div class="mui-media-body".*?>(.*?)</div>'
    matches = re.findall(pattern, response.text, re.DOTALL)
    course_dict = {course_id: course_name.strip() for course_id, course_name in matches}
    return course_dict


async def get_question(JSESSIONID: str, course_id: str) -> dict[str, str]:
    cookies = {
        "JSESSIONID": JSESSIONID,
    }
    headers = {
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "http://112.5.88.114:31101",
        "Pragma": "no-cache",
        "Referer": "http://112.5.88.114:31101/yiban-web/stu/toSubject.jhtml?courseId="
        + course_id,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
        "X-Requested-With": "XMLHttpRequest",
    }
    params = {
        "_": str(time.time_ns())[:13],
    }
    data = {
        "courseId": course_id,
    }

    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            "http://112.5.88.114:31101/yiban-web/stu/nextSubject.jhtml",
            params=params,
            cookies=cookies,
            headers=headers,
            data=data,
        )    
        if response.status_code != 200:
            logger.error("Failed to fetch courses, status code: %s", response.status_code)
            raise Exception("Failed to fetch courses")

    response_data = response.json()
    next_subject = response_data["data"]["nextSubject"]
    
    sub_descript = aes_ecb_decrypt(next_subject["subDescript"])
    sub_type = next_subject["subType"]
    option_count = next_subject["optionCount"]
    uuid = response_data["data"]["uuid"]
    
    options = {}
    for i in range(option_count):
        option_key = f"option{i}"
        if option_key in next_subject:
            decrypted_option = aes_ecb_decrypt(next_subject[option_key])
            option_label = chr(ord("A") + i)
            options[option_label] = decrypted_option
    
    logger.info("Fetched question: %s, type: %s, uuid: %s, options: %d", 
                sub_descript[:50] + "..." if len(sub_descript) > 50 else sub_descript, 
                sub_type, uuid, option_count)
    
    return {
        "sub_descript": sub_descript,
        "sub_type": sub_type,
        "options": str(options),
        "option_count": option_count,
        "uuid": uuid,
    }


async def submit_question(
    JSESSIONID: str, course_id: str, uuid: str, answer: str
) -> bool:
    logger.info("Submitting question for course ID: %s, UUID: %s, answer: %s",
                course_id, uuid, answer)
    cookies = {
        "JSESSIONID": JSESSIONID,
    }
    headers = {
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "http://112.5.88.114:31101",
        "Pragma": "no-cache",
        "Referer": "http://112.5.88.114:31101/yiban-web/stu/toSubject.jhtml?courseId="
        + course_id,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
        "X-Requested-With": "XMLHttpRequest",
    }
    params = {
        "_": str(time.time_ns())[:13],
    }
    data = {
        "answer": answer,
        "courseId": course_id,
        "uuid": uuid,
        "deviceUuid": "",
    }

    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            "http://112.5.88.114:31101/yiban-web/stu/changeSituation.jhtml",
            params=params,
            cookies=cookies,
            headers=headers,
            data=data,
        )

    if response.status_code != 200:
        logger.error("Failed to submit question, status code: %s", response.status_code)
        raise Exception("Failed to submit question")

    if response.json()["message"] == "回答正确！":
        logger.info("Question submitted successfully: %s", response.json()["message"])
        return True
    else:
        logger.warning("Question submission failed: %s", response.json()["message"])
        return False

import requests
import csv
import json
import os
import secrets
import string
from typing import List

from dotenv import load_dotenv
from pprint import pprint

import asyncio
import aiohttp
from aiohttp import client_exceptions


class API360:
    def __init__(self, org_id, access_token):
        self.url = f"https://api360.yandex.net/directory/v1/org/{org_id}"
        self.url_rules = f"https://api360.yandex.net/admin/v1/mail/routing/org/{org_id}/rules"
        self.url_disk = f"https://api360.yandex.net/admin/v1/disk/resources/public?orgId={org_id}"
        self.headers = {
            "Authorization": f"OAuth {access_token}"
        }
        self.org_id = org_id

        self.per_page = 100
        self.temp_password = "00ff00ff00"

    def check_connections_for_deps(self):
        try:
            response = requests.get(f"{self.url}/departments", headers=self.headers)
            if response.status_code != 200:
                print(f"Error during GET request: {response.status_code}. Error message: {response.text}")
                return False
        except Exception as e:
            print(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")
            return False
        return True

    def get_departments_list(self):
        """
        Чтение всех департаментов предприятия
        """
        try:
            response = requests.get(f"{self.url}/departments", headers=self.headers)
            if response.status_code != 200:
                print(f"Error during GET request: {response.status_code}. Error message: {response.text}")
                return []
            deps = response.json().get("departments")
        except requests.exceptions.JSONDecodeError:
            response = requests.get(f"{self.url}/departments", headers=self.headers)
            deps = response.json().get("departments")
        except Exception as e:
            print(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")
            return []

        for i in range(2, response.json().get("pages") + 1):
            successful = False
            while not successful:
                response = requests.get(f"{self.url}/departments?page={i}", headers=self.headers)
                try:
                    deps.extend(response.json().get("departments"))
                    successful = True
                except requests.exceptions.JSONDecodeError:
                    print(f"Error parsing response in method 'get_departments_list': {response.text}")
        return deps

    def get_department_info_by_id(self, department_id: int):
        """
        Посмотреть информацию о подразделении
        :return: json с информацией о подразделении в компании
        """

        response = requests.get(f"{self.url}/departments/{department_id}", headers=self.headers)
        return response.json()

    def get_department_id_by_name(self, department_name, parent_id=1):
        all_deps = self.get_departments_list()
        for dep in all_deps:
            if dep.get("name") == department_name and dep.get("parentId") == parent_id:
                return dep.get("id")

    def delete_department_by_id(self, dep_id: int):
        """
        Delete department by ID
        """
        response = requests.delete(f"{self.url}/departments/{dep_id}", headers=self.headers)
    
        try:
            res = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Error decoding response: {response}")
        except Exception as e:
            print(e.message)
        return res

    def post_create_department_alias(self):
        pass

    def delete_department_alias(self):
        pass

    def patch_department_info(self, department_id=0):
        pass

    def post_create_department(self, department_info: dict):
        """
        Create department
        """
        response = requests.post(f"{self.url}/departments", json=department_info, headers=self.headers)
        if response.status_code == 200:
            print(f"Department {department_info['name']} was created successfully")
        else:
            print(
                f"During creating Department {department_info['name']} occurred error: {response.content.decode(encoding='UTF-8')}")

    def get_groups_list(self):
        """
        Чтение всех департаментов предприятия
        """
        response = requests.get(f"{self.url}/groups", headers=self.headers)
        try:
            groups = response.json().get("groups")
        except requests.exceptions.JSONDecodeError:
            response = requests.get(f"{self.url}/groups", headers=self.headers)
            groups = response.json().get("groups")
        for i in range(2, response.json().get("pages") + 1):
            response = requests.get(f"{self.url}/groups?page={i}", headers=self.headers)
            try:
                groups.extend(response.json().get("groups"))
            except requests.exceptions.JSONDecodeError or TypeError:
                successful = False
                while not successful:
                    response = requests.get(f"{self.url}/groups?page={i}", headers=self.headers)
                    try:
                        groups.extend(response.json().get("groups"))
                        successful = True
                    except requests.exceptions.JSONDecodeError:
                        print(f"Error parsing response in method 'get_groups_list': {response.text}")
        return groups

    def get_group_info_by_id(self, group_id: str):
        """
        Посмотреть информацию about group
        :return: json с информацией о подразделении в компании
        """
        response = requests.get(f"{self.url}/groups/{group_id}", headers=self.headers)
        return response.json()

    def post_create_group(self, group_info: dict):
        """
        Create user group
        """
        response = requests.post(f"{self.url}/groups", json=group_info, headers=self.headers)
        if response.status_code == 200:
            print(f"Group {group_info['name']} was created successfully")
        else:
            print(
                f"FAIL during creating group {group_info['name']} occurred error: {response.content.decode(encoding='UTF-8')}")

    def patch_group_info(self, group_id, data):
        response = requests.patch(f"{self.url}/groups/{group_id}", json=data, headers=self.headers)
        try:
            print(f"Patch group id:{group_id} info: {response.json()}")
        except requests.exceptions.JSONDecodeError:
            successful = False
            while not successful:
                response = requests.patch(f"{self.url}/groups/{group_id}", json=data, headers=self.headers)
                try:
                    print(f"Patch group id:{group_id} info: {response.json()}")
                    successful = True
                except requests.exceptions.JSONDecodeError:
                    print(f"Error parsing response in method 'patch_group_info': {response.text}")

    def delete_group_by_id(self, group_id: str):
        """
        Delete group by ID
        """
        response = requests.delete(f"{self.url}/groups/{group_id}", headers=self.headers)
        res = ''
        try:
            res = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"error decoding response: {response}")
        return res

    def get_group_members_by_id(self, group_id: str):
        response = requests.get(f"{self.url}/groups/{group_id}/members", headers=self.headers)
        res = ""
        try:
            res = response.json().get("users")
        except requests.exceptions.JSONDecodeError:
            successful = False
            while not successful:
                response = requests.get(f"{self.url}/groups/{group_id}/members", headers=self.headers)
                try:
                    res = response.json().get("users")
                    successful = True
                except requests.exceptions.JSONDecodeError:
                    print(f"Error parsing response in method 'get_group_members_by_id': {response.text}")
        return res

    def post_add_member_to_group(self):
        pass

    def get_all_users(self, file=False):
        """
        Get all users of the organisation
        :return:
        """
        response = requests.get(f"{self.url}/users?perPage={self.per_page}", headers=self.headers)
        if not response.ok:
            print(f"{response}:{response.text}")
            return {}
        users = response.json()['users']
        for i in range(2, response.json()["pages"] + 1):
            successful = False
            while not successful:
                response = requests.get(f"{self.url}/users?perPage={self.per_page}&page={i}", headers=self.headers)
                try:
                    users.extend(response.json()['users'])
                    successful = True
                except requests.exceptions.JSONDecodeError as e:
                    print(f"Error occured: {e}")

        # Get all users of the organisation and write info about them in file:
        if file:
            API360.save_file("users_output", users)
        return users

    def get_all_users_id(self, file=False):
        """
        Get all users id in the organisation
        :return:
        """
        users = self.get_all_users()
        ids = []
        for user in users:
            ids.append(user['id'])

        # Get all users ids and write them in file:
        if file:
            API360.save_file("users_ids_output", ids)

        return ids

    def get_all_users_info_by_id(self, ids_lst: List, file=False, min_info=False):
        """
        Get info about users by list ids
        :param min_info:
        :param file: flag to write result in file
        :param ids_lst:
        :return:
        """

        """
        sync option:
                
        users_info = []
        for user_id in ids_lst:
            try:
                response = requests.get(f"{self.url}/users/{user_id}", headers=self.headers)
                while not response.text:
                    print(f'!!!!EMPTY RESPONSE!!!! ID: {user_id}   {response.text}')
                    response = requests.get(f"{self.url}/users/{user_id}", headers=self.headers)
                print(response.text)
                users_info.append(response.json())
            except requests.exceptions.JSONDecodeError:
                print(f'!!!!ERROR!!!! ID: {user_id}   {response.text}')

        """
        # Async:
        users_info, user_false = asyncio.run(self.get_all_users_by_id_async(ids_lst))
        while len(user_false):
            user_info_retry, user_info_false = asyncio.run(self.get_all_users_by_id_async(user_false))
            for user in user_info_retry:
                user_false.remove(user.get('id'))
            users_info.extend(user_info_retry)

        if file:
            if min_info:
                users_minimazed = []
                for user in users_info:
                    user_tmp = {}
                    try:
                        user_tmp['id'] = user['id']
                        user_tmp['nickname'] = user['nickname']
                        user_tmp['email'] = user['email']
                        user_tmp[
                            'name'] = f"{user['name']['last']} {user['name']['first']} {user['name']['middle']}"
                        # user_tmp['link'] = user['contacts'][0]['value']
                        user_tmp['createdAt'] = user['createdAt']
                        users_minimazed.append(user_tmp)
                    except KeyError:
                        print(f'!!!!!!!!!!!!!!Key error for "user": {user}')
                users_info = users_minimazed
            API360.save_file('user_output', users_info)

        return users_info

    def post_create_users(self, users_info: List):
        """
        Creating the new user with the provided dict
        :param users_info: list of the dicts with the new user info
        :return: displays success or error message
        """
        for user in users_info:
            response = requests.post(f"{self.url}/users", json=user, headers=self.headers)
            if response.status_code == 200:
                print(f"User {user['nickname']} was created successfully")
            else:
                print(f"During creating user occurred error: {response.content.decode(encoding='UTF-8')}")

    def delete_user_by_id(self, user_id):
        response = requests.delete(f"{self.url}/users/{user_id}", headers=self.headers)
        res = ''
        try:
            res = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"error decoding response: {response}")
        print(res)
        return res

    def patch_user_password(self, ids: List):
        """
        Reset to default all users passwords in the list
        :param ids:
        :return:
        """
        data = {
            "password": self.temp_password,
            "passwordChangeRequired": True
        }
        for uid in ids:
            response = requests.patch(f"{self.url}/users/{uid}", json=data, headers=self.headers)
            print(response.text)

    def patch_user_info(self, uid, user_data):
        response = requests.patch(f"{self.url}/users/{uid}", json=user_data, headers=self.headers)
        #print(response.json())

    def patch_user_with_unique_password(self, uid: int):
        """
        Reset to default all users passwords in the list
        :param uid:
        :return: password:
        """
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(16))
        data = {
            "password": password,
            "passwordChangeRequired": True
        }
        response = requests.patch(f"{self.url}/users/{uid}", json=data, headers=self.headers)
        return password

    def patch_dismiss_user(self, ids: List, dismiss=False):
        """
        Patch user to dismiss - it does not work
        :param dismiss:
        :param ids:
        :return:
        """
        data = {
            "isDismissed": dismiss
        }
        for uid in ids:
            response = requests.patch(f"{self.url}/users/{uid}", json=data, headers=self.headers)
            print(response.text)

    def get_email_rules(self):
        response = requests.get(f"{self.url_rules}", headers=self.headers)
        print(response)

    def get_public_links(self):
        """
        get all public resources shared by users in organization
        """
        return asyncio.run(self.get_public_links_async(self.get_all_users_id()))

    async def get_public_links_async(self, users_list):

        async with aiohttp.ClientSession("https://api360.yandex.net", headers=self.headers) as session:
            public_resources = {}
            for user_id in users_list:
                user_public_resources = []
                page_num = 1
                params = {
                    'orgId': self.org_id,
                    'userId': user_id,
                    'page': page_num
                }
                async with session.get('/admin/v1/disk/resources/public', params=params) as resp:
                    try:
                        resp_json = dict(await resp.json())
                        print(f"User id {user_id} responses: {resp_json}")
                        while resp_json.get("resources"):
                            user_public_resources.extend(resp_json.get("resources"))
                            page_num += 1
                            params = {
                                'orgId': self.org_id,
                                'userId': user_id,
                                'page': page_num
                            }
                            async with session.get('/admin/v1/disk/resources/public', params=params,
                                                   headers=self.headers) as resp_add:
                                resp_json = dict(await resp_add.json())
                                print(f"User id {user_id} responses: {resp_json}")
                    except aiohttp.client_exceptions.ContentTypeError as e:
                        print(f"Error occured: {e}")
                    except requests.exceptions.JSONDecodeError as e:
                        print(f"Error occured: {e}")
                if len(user_public_resources):
                    public_resources[user_id] = user_public_resources
        return public_resources

    async def get_all_users_by_id_async(self, ids_lst: List):
        """
        """
        users_info = []
        user_false = []
        async with aiohttp.ClientSession("https://api360.yandex.net", headers=self.headers) as session:
            for user_id in ids_lst:
                async with session.get(f'/directory/v1/org/{self.org_id}/users/{user_id}') as resp:
                    if resp.status == 404:
                        print(f'!!!!!!!!!!ID {user_id} is not FOUND!!!!!!!!')
                    elif not resp.ok:
                        print(f"Response --{resp.ok}-- with {user_id}")
                        user_false.append(user_id)
                    else:
                        resp_json = await resp.json()
                        users_info.append(resp_json)
                        print(resp_json)

        return users_info, user_false

    def wipe_all_groups(self):
        for id in list(x.get('id') for x in self.get_groups_list()):
            print(self.delete_group_by_id(id))

    def wipe_all_departments(self):
        for id in list(x.get('id') for x in self.get_departments_list()):
            self.delete_department_by_id(id)

    @staticmethod
    def save_file(file_name, data):
        if isinstance(data, List):
            with open(f"{file_name}.txt", "w", encoding='utf-16') as output:
                for d in data:
                    output.write(f"{d}\n")
        else:
            with open(f'{file_name}.csv', 'w', encoding='utf-16', newline='') as csv_file:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(csv_file, delimiter=',', fieldnames=fieldnames)
                writer.writeheader()
                for user in data:
                    writer.writerow(user)

    def post_user_alias(self):
        pass

    def delete_user_alias(self):
        pass

    def get_user_2fa(self, uid):
        response = requests.get(f"{self.url}/users/{uid}/2fa", headers=self.headers)
        return response.json()


def load_json_file(filename: str):
    with open(filename, "r") as input_file:
        try:
            return json.load(input_file)
        except json.decoder.JSONDecodeError:
            print("Wrong json file format")


def load_user_csv_list(filename):
    users_output = []
    with open(filename, "r", encoding='utf-8-sig') as input_file:
        reader = csv.DictReader(input_file, delimiter=';', quotechar='"')
        for row in reader:
            user_dict = {
                "departmentId": row.get('departmentId', 1),
                "name": {
                    "first": row.get('name', 'Name'),
                    "last": row.get('surname', 'Surname'),
                    "middle": row.get('middle', '')
                },
                "nickname": row.get('yandexmail_login', 'yandexmail_login'),
                "password": row.get('yandexmail_password', 'password'),
                "position": row.get('position', ''),
                "gender": row.get('gender', ''),
                "language": row.get('language', ''),
                "timezone": "Europe/Moscow",
            }
            users_output.append(user_dict)
    return users_output


def get_disk_report(organization):
    # Disk API:
    shared_users = organization.get_public_links()

    pprint(f"TOTAL USERS WITH SHARED FILES:"
           f"{shared_users}")
    ids = []
    for user_id in shared_users.keys():
        ids.append(user_id)

    shared_users_info = organization.get_all_users_info_by_id(ids)
    for detail_info in shared_users_info:
        shared_users[detail_info.get('email')] = shared_users.pop(detail_info.get('id'))

    output = [
        ['username',
         'type',
         'name',
         'publicUrl',
         'size',
         'createdAt'],
    ]
    total_users = 0

    for user, resources in shared_users.items():
        total_users += 1
        for resource in resources:
            per_user = []
            resource.pop('id')
            resource.pop('mimeType')
            resource.pop('modifiedAt')
            per_user.append(user)
            per_user.append(resource.get('type'))
            per_user.append(resource.get('name'))
            per_user.append(resource.get('publicUrl'))
            per_user.append(resource.get('size'))
            per_user.append(resource.get('createdAt'))
            output.append(per_user)

    output.append([f"TOTAL USERS WITH SHARE: {total_users}"])
    with open('disk_report.csv', 'w', encoding='utf-16') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=output[0])

        writer.writeheader()
        w = csv.writer(csvfile)
        w.writerows(output[1:])


def get_2fa_status_organization(organization):
    users = organization.get_all_users_id()
    users_info = organization.get_all_users_info_by_id(users)
    status_2fa = []
    for user in users:
        response = organization.get_user_2fa(user)
        if response.get('message') != 'Internal error':
            status_2fa.append(organization.get_user_2fa(user))
    for user_info in users_info:
        for user_2fa in status_2fa:
            if user_2fa.get('userId') == user_info.get('id'):
                pass
    return status_2fa


if __name__ == "__main__":
    # Get tokens for the organization access:
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)

    organization = API360(os.environ.get('orgId'), os.environ.get('access_token'))

    print(organization.get_all_users())

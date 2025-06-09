import os
from dotenv import load_dotenv
from datetime import datetime
from ldap3 import Server, Connection, ALL, SUBTREE, ALL_ATTRIBUTES, Tls, MODIFY_REPLACE, set_config_parameter
from ldap3.core.exceptions import LDAPBindError
from lib.y360_api.api_script import API360
import logging
import logging.handlers as handlers
import sys

LOG_FILE = "sync_deps.log"

logger = logging.getLogger("sync_deps")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
#file_handler = handlers.TimedRotatingFileHandler(LOG_FILE, when='D', interval=1, backupCount=30, encoding='utf-8')
file_handler = handlers.RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024,  backupCount=20, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def build_group_hierarchy():

    set_config_parameter('DEFAULT_SERVER_ENCODING', 'utf-8')
    set_config_parameter('ADDITIONAL_SERVER_ENCODINGS', 'koi8-r')

    ldap_host = os.environ.get('LDAP_HOST')
    ldap_port = int(os.environ.get('LDAP_PORT'))
    ldap_user = os.environ.get('LDAP_USER')
    ldap_password = os.environ.get('LDAP_PASSWORD')
    ldap_base_dn = os.environ.get('LDAP_BASE_DN')
    #ldap_search_filter = os.environ.get('LDAP_SEARCH_FILTER')
    ldap_search_filter = f"(memberOf={os.environ.get('HAB_ROOT_GROUP')})"

    attrib_list = list(os.environ.get('ATTRIB_LIST').split(','))
    out_file = os.environ.get('AD_DEPS_OUT_FILE')

    server = Server(ldap_host, port=ldap_port, get_info=ALL) 
    try:
        conn = Connection(server, user=ldap_user, password=ldap_password, auto_bind=True)
    except LDAPBindError as e:
        logger.error('Can not connect to LDAP - "automatic bind not successful - invalidCredentials". Exit.')
        logger.error(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")
        return []
            
    conn.search(ldap_base_dn, ldap_search_filter, search_scope=SUBTREE, attributes=attrib_list)
    if conn.last_error is not None:
        logger.error(f'Can not connect to LDAP. Exit.')
        logger.error(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")
        return []

    hierarchy = []
    all_dn = []
    root_group_search_filter = f"(distinguishedName={os.environ.get('HAB_ROOT_GROUP')})"
    conn.search(ldap_base_dn, root_group_search_filter, search_scope=SUBTREE, attributes=attrib_list)
    if conn.last_error is not None:
        logger.error(f'Can not connect to LDAP. Exit.')
        logger.error(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")
        return []
    if len(conn.entries) == 0:
        logger.error(f'Can find root group. Exit.')
        return []

    if conn.entries[0]['displayName'].value is not None:
        name = conn.entries[0]['displayName'].value
    else:
        name = conn.entries[0]['cn'].value

    if conn.entries[0]['mail'].value is not None:
        email = conn.entries[0]['mail'].value
    else:
        email = ''

    hierarchy.append(f"{name}~{email}")
    root_group_name = conn.entries[0]['displayName'].value
    hierarchy, all_dn = build_hierarcy_recursive(conn, ldap_base_dn, attrib_list, root_group_name, conn.entries[0], hierarchy, all_dn)
        
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            for line in hierarchy:
                f.write(f"{line}\n")

    return hierarchy, all_dn

def build_hierarcy_recursive(conn, ldap_base_dn, attrib_list, base, item, hierarchy, all_dn):

    ldap_search_filter = f"(memberOf={item['distinguishedName'].value})"
    conn.search(ldap_base_dn, ldap_search_filter, search_scope=SUBTREE, attributes=attrib_list)

    try:            
        for item in conn.entries:            
            if item['objectCategory'].value.startswith("CN=Group"):
                all_dn.append(item['distinguishedName'].value)
                if item['mail'].value is None:
                    group_mail = ''
                else:
                    group_mail = item['mail'].value
                if item['displayName'].value is not None:
                    hierarchy.append(f"{base};{item['displayName'].value}~{group_mail}")
                    previuos = f"{base};{item['displayName'].value}"
                else:
                    hierarchy.append(f"{base};{item['cn'].value}~{group_mail}")
                    previuos = f"{base};{item['cn'].value}"
                
                hierarchy, all_dn = build_hierarcy_recursive(conn, ldap_base_dn, attrib_list, previuos, item, hierarchy, all_dn)
            elif item['objectCategory'].value.startswith("CN=Person"):
                if item['mail'].value is not None:
                    if item['displayName'].value is not None:
                        hierarchy.append(f"{base}|{item['displayName'].value};{item['mail'].value}")
                    else:
                        hierarchy.append(f"{base}|{item['cn'].value};{item['mail'].value}")

    except Exception as e:
        logger.error(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")
        return [],[]
   
    return hierarchy, all_dn


def generate_deps_list_from_api():
    all_deps_from_api = organization.get_departments_list()
    if len(all_deps_from_api) == 1:
        #print('There are no departments in organozation! Exit.')
        return []
    all_deps = []
    for item in all_deps_from_api:        
        path = item['name'].strip()
        prevId = item['parentId']
        if prevId > 0:
            while not prevId == 1:
                d = next(i for i in all_deps_from_api if i['id'] == prevId)
                path = f'{d["name"].strip()};{path}'
                prevId = d['parentId']
            element = {'id':item['id'], 'parentId':item['parentId'], 'path':path}
            all_deps.append(element)
    return all_deps

def load_heirarchy_from_file(file_path):
    hierarchy = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                hierarchy.append(line)
    return hierarchy

def check_similar_mails_in_hierarchy(hierarchy):
    # Функция проверки наличия похожих почтовых адресов в иерархии
    count_disct = {}
    for item in hierarchy:
        if '|' in item:
            email = item.split('|')[1].split(';')[1]
            if email in count_disct.keys():
                count_disct[email] += 1
            else:
                count_disct[email] = 1

    bad_emails = [k for k, v in count_disct.items() if v > 1]
    if len(bad_emails) > 0:
        logger.error(f'Error! One or several AD users exist in several HAB groups.')
        for email in bad_emails:
            for item in hierarchy:
                if '|' in item:
                    if item.split('|')[1].split(';')[1] == email:
                        logger.error(f'AD User {item.split('|')[1].split(';')[0]} with email {item.split('|')[1].split(';')[1]} found in group {item.split("|")[0]}')
        return False
    return True 

def check_similar_groups_in_hierarchy(all_dn):
    # Функция проверки наличия похожих почтовых адресов в иерархии
    all_dn.sort()
    compared_item = ''
    no_errors = True
    for item in all_dn:
        if item != compared_item:
            compared_item = item
        else:
            logger.error(f'Error! HAB group {compared_item} is member of several groups..')
            no_errors = False
    return  no_errors
   

def create_dep_from_prepared_list(deps_list, max_levels):
    # Фнункция создания департамента из предварительно подготовленного списка
    #print('Create new departments..')
    api_prepared_list = generate_deps_list_from_api()
    for i in range(0, max_levels):
        #Выбираем департаменты, которые будем добавлять на каждом шаге (зависит от уровня level)
        deps_to_add = [d for d in deps_list if d['level'] == i+1]
        need_update_deps = False
        for item in deps_to_add:         
            #Ищем в основном словаре элемент-родитель для данного департамента
            d = next((e for e in deps_list if e['path'] == item['prev']), None)
            item['prevId'] = d['360id']
            #Проверяем, что данный департамент уже добавлен в систему
            t = next((e for e in api_prepared_list if e['path'] == item['path']), None)   
            if t is None:
                department_info = {
                                "name": item['current'],
                                "parentId": d['360id'],
                            }
                if item['email']:
                    department_info['label'] = item['email'].split('@')[0]
                if not dry_run:
                    logger.info(f'Trying to create {item["current"]} department.')
                    result, message = organization.post_create_department(department_info)
                    logger.info(message)
                else:
                    logger.info(f'Dry run: department {item["current"]} will be created')
                need_update_deps = True
        #all_deps_from_api = organization.get_departments_list()
        if need_update_deps:
            api_prepared_list = generate_deps_list_from_api()
        for item in deps_to_add:
            # Ищем в списке департаментов в 360 конкретное значение
            #d = next(i for i in all_deps_from_api if i['name'] == item['current'] and i['parentId'] == item['prevId'])
            d = next(i for i in api_prepared_list if i['path'] == item['path'])
            #Обновляем информацию в final_list для записанных в 360 департаментов
            item['360id'] = d['id']
    
    return deps_list, api_prepared_list


def prepare_deps_list_from_ad_hab(hierarchy):

    deps_list = [{'current': 'All', 'prev': 'None', 'level': 0, '360id': 1, 'prevId': 0, 'path': 'All', 'email': ''}]
    # Формируем уникальный список всей иерархии подразделений (каждое подразделение имеет отдельную строку в списке)
    for item in hierarchy:
        if '|' not in item:
            dep = item.split('~')[0].split(';')
            if item.endswith("~"):
                email = ''
            else:
                email = item.split('~')[1]
            if len(dep) == 1:
                deps_list.append({'current':dep[0], 'prev':'All', 'level':1, '360id':0, 'prevId':0, 'path':'', 'email': email})
            else:
                deps_list.append({'current':dep[-1], 'prev':';'.join(dep[:-1]), 'level':len(dep), '360id':0, 'prevId':0, 'path':'', 'email': email})
    # Фильрация уникальных значений из списка словарей, полученного на предыдущем этапе
    #final_list = [dict(t) for t in {tuple(d.items()) for d in temp_list}]
    # Заполнение поля path (полный путь к подразделению)
    for item in deps_list:
        if not item['current'] == 'All':
            if item['prev'] == 'All':
                item['path'] = item['current']
            else:
                item['path'] = f'{item["prev"]};{item["current"]}'
    # Добавление в 360
    return deps_list

def delete_deps_from_y360(created_deps, deps_from_y360, y360_users):
    for item in deps_from_y360:
        if item['path'] not in [d['path'] for d in created_deps]:
            if item['id'] != 1:
                logger.info(f"Found unused department - {item['path']}")
                for user in y360_users:
                    if user['departmentId'] == item['id']:
                        if not dry_run:
                            logger.info(f"Try to change department of {user['email']} user from _ {item['path']} _ to _ All _")
                            organization.patch_user_info(
                                    uid = user["id"],
                                    user_data={
                                        "departmentId": 1,
                                    })
                        else:
                            logger.info(f"Dry run: department of {user['email']} user will be changed from _ {item['path']} _ to _ All _")
            if not dry_run:
                logger.info(f"Try to delete department {item['path']} from Y360.")
                organization.delete_department_by_id(item['id'])
            else:
                logger.info(f"Dry run: department {item['path']} will be deleted")

def assign_users_to_deps(created_deps, y360_users, ad_users):
    checked_users = []
    for user in ad_users:
        alias = user.split('|')[1].split(';')[1].split('@')[0]
        found_id = ''
        found_user_dep_id = ''
        found_user = None
        for y360_user in y360_users:
            if y360_user['nickname'] == alias:
                found_id = y360_user['id']
                found_user_dep_id = y360_user['departmentId']
                found_user = y360_user
                break
        if not found_id:
            for y360_user in y360_users:
                for contact in y360_user['contacts']:
                    if contact['type'] == 'email':
                        if contact['value'].split('@')[0] == alias:
                            found_id = y360_user['id']
                            found_user_dep_id = y360_user['departmentId']
                            found_user = y360_user
                if found_id:
                    break
        if found_id:
            checked_users.append(found_user)
            ad_deps_path = user.split('|')[:-1][0]
            for deps in created_deps:
                if deps['path'] == ad_deps_path:
                    if deps['360id'] != found_user_dep_id:
                        logger.info(f"User {y360_user['email']} found in Y360, but with wrong department. Change department to {deps['path']}")
                        if not dry_run:
                            organization.patch_user_info(
                                    uid = found_id,
                                    user_data={
                                        "departmentId": deps['360id'],
                                    })
                        else:
                            logger.info(f"Dry run: department of {user['email']} user will be changed from _ {found_user_dep_id} _ to _ {deps['360id']} _")
                    break
        else:
            logger.info(f"AD User {user.split('|')[1]} not found in Y360.")

    users_dict = {}
    for user in y360_users:
        users_dict[user['id']] = user

    y360ids = set([user['id'] for user in y360_users])
    checked_ids  = set([user['id'] for user in checked_users])

    missed_ids = y360ids.difference(checked_ids)
    for id in missed_ids:
        if users_dict[id]['departmentId'] > 1:
            logger.info(f"User {users_dict[id]['email']} not found in Active Directory. Change department to _ All _")
            if not dry_run:
                organization.patch_user_info(
                        uid = id,
                        user_data={
                            "departmentId": 1,
                        })
            else:
                logger.info(f"Dry run: department of user {users_dict[id]['email']} will be changed to _ All _")


if __name__ == "__main__":
    denv_path = os.path.join(os.path.dirname(__file__), '.env_ldap')

    if os.path.exists(denv_path):
        load_dotenv(dotenv_path=denv_path,verbose=True, override=True)
    
    organization = API360(os.environ.get('orgId'), os.environ.get('token'))

    if not organization.check_connections_for_deps():
        logger.error('\n')
        logger.error('Connection to Y360 failed. Check token or Org ID parameters. Exit.\n')
        sys.exit(1)

    dry_run = False
    if os.environ.get('DRY_RUN'):
        if os.environ.get('DRY_RUN').lower() == 'true' or os.environ.get('DRY_RUN').lower() == '1':
            dry_run = True

    logger.info('---------------Start-----------------')
    if dry_run:
        logger.info('- Режим тестового прогона включен (DRY_RUN = True)! Изменения не сохраняются! -')

    hieralchy, all_dn = build_group_hierarchy()
    if not hieralchy:
        logger.error('\n')
        logger.error('List of current departments form Active directory is empty. Exit.\n')
        sys.exit(1)
    if not check_similar_groups_in_hierarchy(all_dn):
        sys.exit(1)
    if not check_similar_mails_in_hierarchy(hieralchy):
        sys.exit(1)

    final_list = prepare_deps_list_from_ad_hab(hieralchy)
    max_levels = max([len(s['path'].split(';')) for s in final_list])
    created_deps, deps_from_y360 = create_dep_from_prepared_list(final_list,max_levels)
    for item in created_deps:
        if item['360id'] == 0:
            logger.error('\n')
            logger.error('Not all departments from Active Directory were saved in Yandex 360. Fix errors. Exit.\n')
            sys.exit(1)
    y360_users = organization.get_all_users()
    if not y360_users:
        logger.error('\n')
        logger.error('List of users from Yandex 360 is empty. Exit.\n')
        sys.exit(1)
    delete_deps_from_y360(created_deps, deps_from_y360, y360_users)
    ad_users = [item for item in hieralchy if '|' in item]
    if not ad_users:
        logger.error('\n')
        logger.error('List of users from Active Directory is empty. Exit.\n')
        sys.exit(1)
    assign_users_to_deps(created_deps, y360_users, ad_users)

    logger.info('---------------End-----------------')

  
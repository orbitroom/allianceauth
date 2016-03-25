import os
import calendar
from datetime import datetime
import hashlib
import sets

from django.db import connections

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

class smfManager:
    SQL_ADD_USER = r"INSERT INTO smf_members (member_name," \
                   r"passwd, email_address, date_registered  " \
                   r") VALUES (%s, %s, %s, %s)"

    SQL_DEL_USER = r"DELETE FROM smf_members where member_name = %s"

    SQL_DIS_USER = r"UPDATE smf_members SET email_address = %s, passwd = %s WHERE member_name = %s"

    SQL_USER_ID_FROM_USERNAME = r"SELECT id_member from smf_members WHERE member_name = %s"
#needs to be fliped  Id_member First
    SQL_ADD_USER_GROUP = r"UPDATE smf_members SET additional_groups = %s WHERE id_member = %s"

    SQL_GET_GROUP_ID = r"SELECT id_group from smf_membergroups WHERE group_name = %s"

    SQL_ADD_GROUP = r"INSERT INTO smf_membergroups (group_name,description) VALUES (%s,%s)"

    SQL_UPDATE_USER_PASSWORD = r"UPDATE smf_members SET passwd = %s WHERE member_name = %s"

    SQL_REMOVE_USER_GROUP = r"DELETE FROM smf_members WHERE id_member = %s AND additional_groups = %s "

    SQL_GET_ALL_GROUPS = r"SELECT id_group, group_name FROM smf_membergroups"

    SQL_GET_USER_GROUPS = r"SELECT additional_groups FROM smf_members WHERE member_name = %s"

    SQL_ADD_USER_AVATAR = r"UPDATE smf_members SET avatar = %s WHERE member_name = %s"
    
    SQL_CLEAR_USER_PERMISSIONS = r"UPDATE smf_members SET additional_groups = '0' id_group = '0' WHERE id_member = %s"



    def __init__(self):
        pass

    @staticmethod
    def __add_avatar(member_name, characterid):
        logger.debug("Adding EVE character id %s portrait as smf avater for user %s" % (characterid, member_name))
        avatar_url = "https://image.eveonline.com/Character/" + characterid + "_64.jpg"
        cursor = connections['smf'].cursor()
        id_member = smfManager.__get_user_id(member_name)
        cursor.execute(smfManager.SQL_ADD_USER_AVATAR, [avatar_url, id_member])

    @staticmethod
    def __generate_random_pass():
        return os.urandom(8).encode('hex')

    @staticmethod
    def __gen_hash(member_name_clean, passwd):
        return hashlib.sha1((member_name_clean) + passwd).hexdigest()

    @staticmethod
    def __santatize_member_name(member_name):
        sanatized = member_name.replace(" ", "_")
        sanatized = sanatized.replace("'", "")
        return sanatized.lower()

    @staticmethod
    def __get_group_id(group_name):
        logger.debug("Getting smf group id for group_name %s" % group_name)
        cursor = connections['smf'].cursor()
        cursor.execute(smfManager.SQL_GET_GROUP_ID, [group_name])
        row = cursor.fetchone()
        logger.debug("Got smf group id %s for group_name %s" % (row[0], group_name))
        return row[0]

    @staticmethod
    def __get_user_id(member_name):
        logger.debug("Getting smf user id for member_name %s" % member_name)
        cursor = connections['smf'].cursor()
        cursor.execute(smfManager.SQL_USER_ID_FROM_USERNAME, [member_name])
        row = cursor.fetchone()
        if row is not None:
            logger.debug("Got smf user id %s for member_name %s" % (row[0], member_name))
            return row[0]
        else:
            logger.error("member_name %s not found on smf. Unable to determine id_user." % member_name)
            return None

    @staticmethod
    def __get_all_groups():
        logger.debug("Getting all smf groups.")
        cursor = connections['smf'].cursor()
        cursor.execute(smfManager.SQL_GET_ALL_GROUPS)
        rows = cursor.fetchall()
        out = {}
        for row in rows:
            out[row[1]] = row[0]
        logger.debug("Got smf groups %s" % out)
        return out

    @staticmethod
    def __get_user_groups(member_name):
        logger.debug("Getting smf member_name %s groups" % member_name)
        cursor = connections['smf'].cursor()
        cursor.execute(smfManager.SQL_GET_USER_GROUPS, [member_name])
        out = cursor.fetchall()
        
        logger.debug("Got user %s smf groups %s" % (member_name, out))
        return out

    @staticmethod
    def __get_current_utc_date():
        d = datetime.utcnow()
        unixtime = calendar.timegm(d.utctimetuple())
        return unixtime

    @staticmethod
    def __create_group(group_name):
        logger.debug("Creating smf group %s" % group_name)
        cursor = connections['smf'].cursor()
        cursor.execute(smfManager.SQL_ADD_GROUP, [group_name, group_name])
        logger.info("Created smf group %s" % group_name)
        return smfManager.__get_group_id(group_name)

    @staticmethod
    def __add_user_to_group(additional_groups, id_member):
        logger.debug("Adding smf user id %s to additional _groups %s" % (id_member, additional_groups))
        try:
            cursor = connections['smf'].cursor()
            cursor.execute(smfManager.SQL_ADD_USER_GROUP, [additional_groups, id_member])
            logger.info("Added smf id_member %s to additional_groups %s" % (id_member, additional_groups))
        except:
            logger.exception("Unable to add smf id_member %s to additional_groups %s" % (id_member, additional_groups))
            pass

    @staticmethod
    def __remove_user_from_group(id_member, additional_groups):
        logger.debug("Removing smf id_member %s from group %s" % (id_member, additional_groups))
        try:
            cursor = connections['smf'].cursor()
            cursor.execute(smfManager.SQL_REMOVE_USER_GROUP, [id_member, additional_groups])
            #cursor.execute(smfManager.SQL_CLEAR_USER_PERMISSIONS, [id_member])
            logger.info("Removed smf id_member %s from group %s" % (id_member, additional_groups))
        except:
            logger.exception("Unable to remove smf id_member %s from group %s" % (id_member, additional_groups))
            pass

    @staticmethod
    def add_user(member_name, email_address, characterid):
        logger.debug("Adding smf user with member_name %s, email_address %s, characterid %s" % (member_name, email_address, characterid))
        cursor = connections['smf'].cursor()

        member_name_clean = smfManager.__santatize_member_name(member_name)
        passwd = smfManager.__generate_random_pass()
        pwhash = smfManager.__gen_hash(member_name_clean, passwd)
        logger.debug("Proceeding to add smf user %s and pwhash starting with %s" % (member_name, pwhash[0:5]))
        # check if the username was simply revoked
        if smfManager.check_user(member_name):
            logger.warn("Unable to add smf user with username %s - already exists. Updating user instead." % member_name)
            smfManager.__update_user_info(member_name_clean, email_address, pwhash)
        else:
            try:

                cursor.execute(smfManager.SQL_ADD_USER, [member_name_clean, passwd, email_address, smfManager.__get_current_utc_date()])
                smfManager.__add_avatar(member_name, characterid)
                logger.info("Added smf member_name %s" % member_name)
            except:
                logger.warn("Unable to add smf user %s" % member_name)
                pass

        return member_name, passwd

    @staticmethod
    def disable_user(member_name):
        logger.debug("Disabling smf user %s" % member_name)
        cursor = connections['smf'].cursor()
        passwd = os.urandom(32).encode('hex')
        revoke_email = "revoked@" + settings.DOMAIN
        try:
            cursor.execute(smfManager.SQL_DIS_USER, [revoke_email, passwd, member_name])
            id_member = smfManager.__get_user_id(member_name)
            #cursor.execute(smfManager.SQL_DEL_AUTOLOGIN, [id_member])
            #cursor.execute(smfManager.SQL_DEL_SESSION, [id_member])
            smfManager.update_groups(member_name, [])
            logger.info("Disabled smf user %s" % member_name)
            return True
        except TypeError as e:
            logger.exception("TypeError occurred while disabling user %s - failed to disable." % member_name)
            return False

    @staticmethod
    def delete_user(member_name):
        logger.debug("Deleting smf user %s" % member_name)
        cursor = connections['smf'].cursor()

        if smfManager.check_user(member_name):
            cursor.execute(smfManager.SQL_DEL_USER, [member_name])
            logger.info("Deleted smf user %s" % member_name)
            return True
        logger.error("Unable to delete smf user %s - user not found on smf." % member_name)
        return False

    @staticmethod
    def update_groups(member_name, additional_groups):
        id_member = smfManager.__get_user_id(member_name)
        logger.debug("Updating smf user %s with id %s with group id %s" % (member_name, id_member, additional_groups))
        if id_member is not None:
            forum_groups = smfManager.__get_all_groups()
            user_groups = set(smfManager.__get_user_groups(member_name))
            logger.info("Current groups for %s are %s" % (member_name, user_groups))
            logger.info("Updating smf user %s groups %s" % (member_name, additional_groups))
            for g in forum_groups:
                if not g in forum_groups:
                    forum_groups[g] = smfManager.__create_group(g)
                smfManager.__add_user_to_group(additional_groups, id_member)



    @staticmethod
    def remove_group(member_name, group_name):
        logger.debug("Removing smf user %s from group %s" % (member_name, group_name))
        cursor = connections['smf'].cursor()
        id_member = smfManager.__get_user_id(member_name)
        if id_member is not None:
            additional_groups = smfManager.__get_group_id(group_name)
            print additional_groups
            group_string = smfManager.__get_user_groups(member_name)
            print group_string
            #group_list = group_string.split(',')
#transfer to list then use for statement to pull out the group name
            group_list_finish = (group_string) - (additional_groups)
            #group_list_add = ",".join(group_list_finish)

            logger.info("result of modified groups %s" % (group_list_finish))


    @staticmethod
    def check_user(member_name):
        logger.debug("Checking smf username %s" % member_name)
        cursor = connections['smf'].cursor()
        cursor.execute(smfManager.SQL_USER_ID_FROM_USERNAME, [smfManager.__santatize_member_name(member_name)])
        row = cursor.fetchone()
        if row:
            logger.debug("Found user %s on smf" % member_name)
            return True
        logger.debug("User %s not found on smf" % member_name)
        return False

    @staticmethod
    def update_user_password(member_name, characterid, passwd=None):
        logger.debug("Updating smf user %s password" % member_name)
        cursor = connections['smf'].cursor()
        if not passwd:
            passwd = smfManager.__generate_random_pass()
        if smfManager.check_user(member_name):
            pwhash = smfManager.__gen_hash(passwd)
            logger.debug("Proceeding to update smf user %s password with pwhash starting with %s" % (member_name, pwhash[0:5]))
            cursor.execute(smfManager.SQL_UPDATE_USER_PASSWORD, [pwhash, member_name])
            #smfManager.__add_avatar(member_name, characterid)
            logger.info("Updated smf user %s passwd." % member_name)
            return passwd
        logger.error("Unable to update smf user %s password - user not found on smf." % member_name)
        return ""

    @staticmethod
    def __update_user_info(member_name, email_address, passwd):
        logger.debug("Updating smf user %s info: username %s password of length %s" % (member_name, email_address, len(passwd)))
        cursor = connections['smf'].cursor()
        try:
            cursor.execute(smfManager.SQL_DIS_USER, [email_address, passwd, member_name])
            logger.info("Updated smf user %s info" % member_name)
        except:
            logger.exception("Unable to update smf user %s info." % member_name)
            pass

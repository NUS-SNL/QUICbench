
def get_remote_cmd(remote_hostname, cmd_lst):
    return ["ssh", remote_hostname, " ".join(cmd_lst)]

def get_remote_cmd_sudo(remote_hostname, remote_pw_path, cmd):
    return "cat {} | ssh {} cat \| sudo --prompt="" -S -- \"{}\"".format(remote_pw_path, remote_hostname, cmd)

def get_remote_cmd_sudo_array(remote_hostname, remote_pw_path, cmd):
    return get_remote_cmd_sudo(remote_hostname, remote_pw_path, cmd).split(" ")

def get_scp_file_to_remote_cmd(remote_hostname, local_file_path, remote_dir):
    return ["scp", local_file_path, "{}:{}".format(remote_hostname, remote_dir)]

def get_pkill_cmd(pattern):
 return ["pkill", "-f", "\'{}\'".format(pattern)]

def get_pkill_remote_cmd(remote_hostname, pattern):
    kill_cmd = get_remote_cmd(remote_hostname, get_pkill_cmd(pattern))
    return kill_cmd

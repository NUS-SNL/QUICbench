
def get_remote_cmd(remote_hostname, cmd_lst):
    return ["ssh", remote_hostname, " ".join(cmd_lst)]

def get_remote_cmd_sudo(remote_hostname, remote_pw_path, cmd):
    return "cat {} | ssh {} cat \| sudo --prompt="" -S -- \"{}\"".format(remote_pw_path, remote_hostname, cmd)

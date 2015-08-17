import os
import sys
from rpython.rlib.rposix import _as_bytes, chdir
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.rsocket import gethostname

def warn(msg):
  print '[powerline-bash] ', msg

class Segment(object):
  def __init__(self, content, fg, bg, seperator, seperator_fg):
    self.content = content
    self.fg = fg
    self.bg = bg
    self.seperator = seperator
    self.seperator_fg = seperator_fg

class Args(object):
  def __init__(self, shell, mode):
    self.shell = shell
    self.mode = mode
    self.cwd_max_depth = 8
    self.cwd_only = False
    self.prev_error = 0

class Powerline(object):
  symbols = {
    'compatible': {
      'lock': u'RO',
      'network': u'SSH',
      'separator': u'\u25B6',
      'separator_thin': u'\u276F'
    },
    'patched': {
      'lock': u'\uE0A2',
      'network': u'\uE0A2',
      'separator': u'\uE0B0',
      'separator_thin': u'\uE0B1'
    },
    'flat': {
      'lock': u'',
      'network': u'',
      'separator': u'',
      'separator_thin': u''
    }
  }

  color_templates = {
    'bash': '\\[\\e%s\\]',
    'zsh': '%%{%s%%}',
    'bare': '%s',
  }

  def __init__(self, args, cwd):
    args = Args('bare', 'patched')
    self.args = args
    self.cwd = cwd
    mode, shell = args.mode, args.shell
    self.color_template = self.color_templates[shell]
    #self.reset = self.color_template.format('[0m')
    self.reset = '' + '[0m'
    self.lock = Powerline.symbols[mode]['lock']
    self.network = Powerline.symbols[mode]['network']
    self.separator = Powerline.symbols[mode]['separator']
    self.separator_thin = Powerline.symbols[mode]['separator_thin']
    self.segments = []

  def color(self, prefix, code):
    if code is None:
      return ''
    else:
      return '' + ('[' + prefix + ';5;' + str(code) + 'm')
      #return self.color_template.format('[%s;5;%sm'.format(prefix, code))

  def fgcolor(self, code):
    return self.color('38', code)

  def bgcolor(self, code):
    return self.color('48', code)

  def append(self, content, fg, bg, separator=None, separator_fg=None):
    if separator is None:
      separator = self.separator.encode('utf-8')
    if separator_fg is None:
      separator_fg = str(bg)
    self.segments.append(Segment(content, fg, bg, separator, int(separator_fg)))
    #self.segments.append((content, fg, bg, '\u25B6', bg))
      #separator if separator is not None else self.separator,
      #separator_fg if separator_fg is not None else bg))


  def draw(self):
    builder = StringBuilder()
    for i in range(len(self.segments)):
      builder.append(self.draw_segment(i))
    builder.append(self.reset)
    builder.append(' ')
    return builder.build()

  def draw_segment(self, idx):
    segment = self.segments[idx]
    next_segment = self.segments[idx + 1] if idx < len(self.segments)-1 else None
    builder = StringBuilder()
    builder.append(self.fgcolor(segment.fg))
    builder.append(self.bgcolor(segment.bg))
    builder.append(segment.content)
    if next_segment:
      builder.append(self.bgcolor(next_segment.bg))
      builder.append(self.fgcolor(segment.seperator_fg))
      builder.append(segment.seperator)
    else:
      builder.append(self.reset)
      builder.append(self.fgcolor(segment.seperator_fg))
      builder.append(segment.seperator)
    return builder.build()
  
def get_valid_cwd():
  """ We check if the current working directory is valid or not. Typically
    happens when you checkout a different branch on git that doesn't have
    this directory.
    We return the original cwd because the shell still considers that to be
    the working directory, so returning our guess will confuse people
  """
  cwd = os.environ[_as_bytes('PWD')]
  parts = cwd.split(os.sep)
  up = cwd
  while parts and not os.path.exists(up):
    parts.pop()
    up = os.sep.join(parts)
  chdir(up)
  return cwd

class Color(object):
  """
  This class should have the default colors for every segment.
  Please test every new segment with this theme first.
  """
  USERNAME_FG = 250
  USERNAME_BG = 240
  USERNAME_ROOT_BG = 124

  HOSTNAME_FG = 250
  HOSTNAME_BG = 238

  HOME_SPECIAL_DISPLAY = True
  HOME_BG = 31  # blueish
  HOME_FG = 15  # white
  PATH_BG = 237  # dark grey
  PATH_FG = 250  # light grey
  CWD_FG = 254  # nearly-white grey
  SEPARATOR_FG = 244

  READONLY_BG = 124
  READONLY_FG = 254

  SSH_BG = 166 # medium orange
  SSH_FG = 254

  REPO_CLEAN_BG = 148  # a light green color
  REPO_CLEAN_FG = 0  # black
  REPO_DIRTY_BG = 161  # pink/red
  REPO_DIRTY_FG = 15  # white

  JOBS_FG = 39
  JOBS_BG = 238

  CMD_PASSED_BG = 236
  CMD_PASSED_FG = 15
  CMD_FAILED_BG = 161
  CMD_FAILED_FG = 15

  SVN_CHANGES_BG = 148
  SVN_CHANGES_FG = 22  # dark green

  VIRTUAL_ENV_BG = 35  # a mid-tone green
  VIRTUAL_ENV_FG = 00

def add_username_segment(powerline):
  import os
  if powerline.args.shell == 'bash':
    user_prompt = ' \\u '
  elif powerline.args.shell == 'zsh':
    user_prompt = ' %n '
  else:
    user_prompt = ' ' + os.environ[_as_bytes('USER')] + ' '

  if os.environ[_as_bytes('USER')] == 'root':
    bgcolor = Color.USERNAME_ROOT_BG
  else:
    bgcolor = Color.USERNAME_BG

  powerline.append(user_prompt, Color.USERNAME_FG, bgcolor)

def add_hostname_segment(powerline):
  if powerline.args.shell == 'bash':
    host_prompt = ' \\h '
  elif powerline.args.shell == 'zsh':
    host_prompt = ' %m '
  else:
    host_prompt = ' ' + gethostname().split('.')[0] + ' '

  powerline.append(host_prompt, Color.HOSTNAME_FG, Color.HOSTNAME_BG)

sep = os.sep.decode('utf-8')

def get_short_path(cwd):
  home = os.environ[_as_bytes('HOME')]
  names = cwd.split(sep)
  if names[0] == u'': names = names[1:]
  path = u''
  for i in range(len(names)):
    path += sep + names[i]
    if os.path.samefile(path.encode('utf-8'), home):
      return [u'~'] + names[i+1:]
  if not names[0]:
    return [u'/']
  return names

def add_cwd_segment(powerline):
  cwd = powerline.cwd or os.environ[_as_bytes('PWD')]
  names = get_short_path(cwd.decode('utf-8'))

  max_depth = powerline.args.cwd_max_depth
  if len(names) > max_depth:
    i = 2 - max_depth
    assert i > 0
    names = names[:2] + [u'\u2026'] + names[i:]

  if not powerline.args.cwd_only:
    for n in names[:-1]:
      if n == u'~' and Color.HOME_SPECIAL_DISPLAY:
        powerline.append(' ' + n.encode('utf-8') + ' ', Color.HOME_FG, Color.HOME_BG)
      else:
        powerline.append(' ' + n.encode('utf-8') + ' ', Color.PATH_FG, Color.PATH_BG, powerline.separator_thin.encode('utf-8'), str(Color.SEPARATOR_FG))

  if names[-1] == u'~' and Color.HOME_SPECIAL_DISPLAY:
    powerline.append(' ' + names[-1].encode('utf-8') + ' ', Color.HOME_FG, Color.HOME_BG)
  else:
    powerline.append(' ' + names[-1].encode('utf-8') + ' ', Color.CWD_FG, Color.PATH_BG)

def add_root_indicator_segment(powerline):
  root_indicators = {
    'bash': ' \\$ ',
    'zsh': ' \\$ ',
    'bare': ' $ ',
  }
  bg = Color.CMD_PASSED_BG
  fg = Color.CMD_PASSED_FG
  if powerline.args.prev_error != 0:
    fg = Color.CMD_FAILED_FG
    bg = Color.CMD_FAILED_BG
  powerline.append(root_indicators[powerline.args.shell], fg, bg)

def entry_point(argv):
  powerline = Powerline(None, get_valid_cwd())
  add_username_segment(powerline)
  add_hostname_segment(powerline)
  add_cwd_segment(powerline)
  add_root_indicator_segment(powerline)
  print powerline.draw()
  return 0

def target(*args):
  return entry_point, None

if __name__ == '__main__':
  import sys
  entry_point(sys.argv)

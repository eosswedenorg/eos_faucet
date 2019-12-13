
def format_plural(num, unit, prefix='s') :
    if num > 1 :
        unit += prefix
    return '{} {}'.format(num, unit)

def format_timespan(s) :
  m, s = divmod(s, 60)
  h, m = divmod(m + (s > 0), 60) # Round up to nearest minute (becuse we don't show seconds)
  parts = []

  if h > 0 :
    parts.append(format_plural(h, "hour"))
  if m > 0 :
    parts.append(format_plural(m, "minute"))
  return ', '.join(parts)

def remote_ip(request) :
  return request.headers.get("X-Real-IP") or \
         request.headers.get("X-Forwarded-For") or \
         request.remote_ip

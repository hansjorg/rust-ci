# Varnish VCL config for www.rust-ci.org

backend nginx {
  .host = "127.0.0.1";
  .port = "8000";
}

acl purge {
  "localhost";
}

sub vcl_recv {
  set req.backend = nginx;

  if ((req.url ~ "/p/") || (req.url ~ "/admin") || (req.url ~ "/artifacts") || (req.url ~ "/callback")) {
    return(pass);
  }

  # Normalize host header (for test env)
  set req.http.Host = "www.rust-ci.org";

  # Remove cookies from request
  unset req.http.cookie;

  if (req.request == "PURGE") {
    # Ignore query string (python-varnish adds "?" to PURGE URLs)
    set req.url = regsub(req.url, "\?.*$", "");
    if (!client.ip ~ purge) {
      error 405 "Not allowed.";
    }
    return (lookup);
  }
}

sub vcl_hit {
  if (req.request == "PURGE") {
    purge;
    error 200 "Purged.";
  }
}

sub vcl_miss {
  if (req.request == "PURGE") {
    purge;
    error 200 "Purged.";
  }
}

sub vcl_fetch {
  # Remove set-cookie from backend response
  if (!(req.url ~ "/p/") && !(req.url ~ "/admin") && !(req.url ~ "/artifacts") && !(req.url ~ "/callback")) {
    unset beresp.http.set-cookie;
  }

  # Remove Expires from backend
  unset beresp.http.expires;

  # Set the clients TTL on this object
  if (req.url ~ "^/static") {
    set beresp.http.cache-control = "max-age=31536000";
  } else {
    set beresp.http.cache-control = "max-age=0";
  }

  # Set how long Varnish will keep it
  set beresp.ttl = 10w;

  # marker for vcl_deliver to reset Age:
  set beresp.http.magicmarker = "1";
}

sub vcl_deliver {
  if (resp.http.magicmarker) {
    # Remove the magic marker
    unset resp.http.magicmarker;

    # By definition we have a fresh object
    set resp.http.age = "0";
  }

  # Set HIT/MISS indicator
  if (obj.hits > 0) {
    set resp.http.X-Cache = "HIT";
  } else {
    set resp.http.X-Cache = "MISS";
  } 
}


while IFS== read -r key value; do
    printf -v "$key" %s "$value" && export "$key" && echo "${key}=$(printenv $key)"
done <config.env

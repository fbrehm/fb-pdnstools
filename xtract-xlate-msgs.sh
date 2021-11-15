#!/bin/bash

set -e
set -u

base_dir=$( dirname "$0" )
cd "${base_dir}" || exit 99

locale_dir="locale"
locale_domain="fb_pdnstools"
pot_file="${locale_dir}/${locale_domain}.pot"
po_with="99"
my_address="${DEBEMAIL:-frank@brehm-online.com}"

pkg_version=$( head -n 1 debian/changelog | sed -e 's/^[^(]*(//' -e 's/).*//' )
echo "Package-Version: '${pkg_version}'"

pybabel extract bin/* lib \
    -o "${pot_file}" \
    -F etc/babel.ini \
    --width=${po_with} \
    --sort-by-file \
    --msgid-bugs-address="${my_address}" \
    --copyright-holder="Frank Brehm, Berlin" \
    --project="${locale_domain}" \
    --version="${pkg_version}"

sed -i -e "s/FIRST AUTHOR/Frank Brehm/g" -e "s/<EMAIL@ADDRESS>/<${my_address}>/g" "${pot_file}"

for lang in de_DE en_US ; do
    po_file="${locale_dir}/${lang}/LC_MESSAGES/${locale_domain}.po"
    if [[ ! -f "${po_file}" ]] ; then
        pybabel init --domain "${locale_domain}" \
            --input-file "${pot_file}" \
            --output-dir "${locale_dir}" \
            --locale "${lang}" \
            --width ${po_with}
    else
        pybabel update --domain "${locale_domain}" \
            --input-file "${pot_file}" \
            --output-dir "${locale_dir}" \
            --locale "${lang}" \
            --width ${po_with} \
            --ignore-obsolete \
            --update-header-comment
    fi

    # Updating project version
    sed -i -e "s/^\(\"Project-Id-Version:[ 	][ 	]*[^ 	][^ 	]*[ 	][ 	]*\)[^ 	\\][^ 	\\]*/\1${pkg_version}/i" "${po_file}"

done

# vim: ts=4 list

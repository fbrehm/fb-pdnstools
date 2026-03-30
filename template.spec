# vim: filetype=spec

%define version @@@Version@@@
%define builddir %{_builddir}/python%{python3_pkgversion}-fb-pdnstools-%{version}

Name:           python%{python3_pkgversion}-fb-pdnstools
Version:        %{version}
Release:        @@@Release@@@%{?dist}
Summary:	Python module to handle with PowerDNS

Group:          Development/Languages/Python
License:        LGPL-3
Distribution:   Frank Brehm
URL:            https://github.com/fbrehm/fb-fb-pdnstools
Source0:        fb-pdnstools.%{version}.tar.gz

BuildRequires:	gettext
BuildRequires:  python%{python3_pkgversion}
BuildRequires:  python%{python3_pkgversion}-babel
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-fb-tools >= 3.0.0
BuildRequires:  python%{python3_pkgversion}-libs
BuildRequires:  python%{python3_pkgversion}-semver
BuildRequires:  python%{python3_pkgversion}-six
BuildRequires:  pyproject-rpm-macros

Requires:       python%{python3_pkgversion}
Requires:       python%{python3_pkgversion}-babel
Requires:       python%{python3_pkgversion}-fb-tools >= 3.0.0
Requires:       python%{python3_pkgversion}-libs
Requires:       python%{python3_pkgversion}-requests
Requires:       python%{python3_pkgversion}-semver
Requires:       python%{python3_pkgversion}-six
Requires:       python%{python3_pkgversion}-urllib3
BuildArch:      noarch

%description
Python module to handle with PowerDNS

This is the Python%{python3_pkgversion} version.

In this package are contained the following scripts:
 * pdns-bulk-remove

%prep
echo "Preparing '${builddir}-' ..."
echo "Pwd: $( pwd )"
%autosetup -p1 -v

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files fb_pdnstools

echo "Whats in '%{builddir}':"
ls -lA '%{builddir}'

echo "Whats in '%{buildroot}':"
ls -lA '%{buildroot}'

%files -f %{pyproject_files}
%defattr(-,root,root,-)
%license LICENSE
%doc LICENSE README.md CHANGELOG.md pyproject.toml debian/changelog
%{_bindir}/*
%{_datadir}/*

%changelog

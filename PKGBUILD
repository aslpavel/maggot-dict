# Maintainer: Pavel Aslanov <asl.pavel@gmail.com>
pkgname=maggot-dict-git
pkgver=2
pkgrel=1
pkgdesc='Pure python (for now console based) dictionary'
arch=('any')
url='https://github.com/aslpavel/maggot-dict'
license=('GPL')
depends=(python)
makedepends=(git)
conflicts=()
provides=()
source=()
md5sums=()

_gitroot='git://github.com/aslpavel/maggot-dict.git'
_gitname='maggot-dict'

#------------------------------------------------------------------------------#
# Build                                                                        #
#------------------------------------------------------------------------------#
build () {
    cd $srcdir

    msg 'Connecting to GIT server ...'
    if [ -d $_gitname ]; then
        cd $_gitname
        git pull origin
        git submodule update --recursive
    else
        git clone $_gitroot $_gitname
        cd $_gitname
        git submodule update --init --recursive
    fi
    git submodule update
    msg 'The local files are updated'
}

#------------------------------------------------------------------------------#
# Package                                                                      #
#------------------------------------------------------------------------------#
package () {
    cd $srcdir/$_gitname
    make DESTDIR=$pkgdir install
}

# vim: nu ft=sh columns=120 :

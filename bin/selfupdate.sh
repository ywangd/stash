echo StaSh is trying to selfupdate ...
wget https://github.com/ywangd/stash/archive/buggy.zip -o $STASH_ROOT/stash.zip
unzip $STASH_ROOT/stash.zip -d $STASH_ROOT
rm $STASH_ROOT/stash.zip
echo Done

echo StaSh is trying to selfupdate ...
wget https://github.com/ywangd/stash/archive/$SELFUPDATE_BRANCH.zip -o $STASH_ROOT/stash.zip
unzip $STASH_ROOT/stash.zip -d $STASH_ROOT
rm $STASH_ROOT/stash.zip
rm -f $STASH_ROOT/dummyui.py
rm -f $STASH_ROOT/dummyconsole.py
echo Done

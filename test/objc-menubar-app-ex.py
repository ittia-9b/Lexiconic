from AppKit import NSApplication, NSStatusBar, NSVariableStatusItemLength, NSMenu, NSMenuItem
from PyObjCTools import AppHelper

class MenuBarApp:
    def __init__(self):
        self.app = NSApplication.sharedApplication()
        statusbar = NSStatusBar.systemStatusBar()
        self.item = statusbar.statusItemWithLength_(NSVariableStatusItemLength)
        self.item.setTitle_("🔊")  # Unicode icon or use setImage_ with an NSImage

        # Build the menu
        menu = NSMenu.alloc().init()
        say_hi = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Say Hi", "sayHi:", "")
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "terminate:", "")

        menu.addItem_(say_hi)
        menu.addItem_(quit_item)
        self.item.setMenu_(menu)

        # Assign action method to class (needs to be an Obj-C selector)
        self.sayHi_ = self.sayHi

    def sayHi(self, sender):
        print("Hello from the menu bar app!")

if __name__ == "__main__":
    import sys
    app = MenuBarApp()
    AppHelper.runEventLoop()

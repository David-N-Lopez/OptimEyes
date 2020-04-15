# Optimeyes

## Usage

### How to install and configure the extension

1. Install the extension from the Chrome store...
1. Upon initial installation, the extension will ask for permission to access
the webcam. After granting permission, you can close the welcome page.
   * Note  that all the images taken will be viewed by a group of students 
     ans then deleted. 
     So try to be careful!


## Code breakdown

welcome.[html/js] - Page launched on initial extension installation which
requests webcam access for the extension.

popup.[html/js] - Browser action popup page. Displays the webcam and has
controls for training the scrolling gestures and enabling/disabling scrolling.
Passes messages to the background page to do the actual processing.

background.[html/js] - Contains all the machine learning logic for the
extension. Trains the KNN image classifier when in training mode, infers which
scrolling gestures are being performed when in inference mode, and sends
messages to the content script to perform scrolling.

content.js - Content script running with webpages loaded in Chrome. Calls
window.scrollBy to scroll webpages and places visual indicators on the page when
scrolling.


/*
    gallery.js    Mike Glover <mglover@pobox.com>
    this is the code that let's you zoom in on images on the
    gallery pages and view them as a slideshow.
*/

window.onload = function () {
    elOverlay = document.getElementById("overlay");
    elBody = document.getElementById("container");
    elPrev = document.getElementById("prev");
    elNext = document.getElementById("next");
    elClose = document.getElementById('close');

    photos = document.getElementsByClassName("photo");

    function hideZoomer() {
        elOverlay.classList.add('hidden')
        elBody.classList.remove('fade')
    }

    function showZoomer(idx) {
        elPhoto = photos[idx];
        elOrigImg = elPhoto.getElementsByTagName('img')[0];
        elOrigCap = elPhoto.getElementsByTagName('span')[0];
        elZoomImg = elOverlay.getElementsByTagName('img')[0];
        elZoomCap = elOverlay.getElementsByClassName('caption')[0];
        elZoomImg.src = elOrigImg.src;
        elZoomCap.innerHTML = elOrigCap.innerHTML;

        elBody.classList.add("fade")
        elOverlay.classList.remove('hidden')

        if ( idx > 1) {
            elPrev.onclick = function(e) {
                e.stopPropagation();
                console.log("prev", idx);
                hideZoomer();
                showZoomer(idx - 1);
            }
            elPrev.disabled = false;
        }  else {
            elPrev.disabled = true;
        }
        if ( idx < photos.length-1 ) {
            elNext.onclick = function(e) {
                e.stopPropagation();
                console.log("next", idx);
                hideZoomer();
                showZoomer(idx + 1);
            }
            elNext.disabled = false;
        } else {
            elNext.disabled = true;
        }
    }

    function addZoomer (idx) {
        elPhoto = photos[idx];
        elPhoto.onclick = function (e) {
            e.stopPropagation();
            console.log('photo click', idx);
            showZoomer(idx);
        }
    }

    for (i=0;i<photos.length;i++) {
        addZoomer(i);
    }

    elClose.onclick = function(e) {
        e.stopPropagation();
        console.log('close');
        hideZoomer();
    }

    elBody.onclick = function () {
        console.log('body click');
        hideZoomer();
    }
}

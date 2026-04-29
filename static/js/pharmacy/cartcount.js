// cartcount.js
  window.addEventListener("pageshow", function (event) {
    // persist true means the page was loaded from cache (back button)
    updateCartCount(); 
});

window.onpageshow = function(event) {
    // اگر پیج براؤزر کے کیشے (Cache) سے لوڈ ہوا ہے
    if (event.persisted) {
        // تو زبردستی پیج کو دوبارہ لوڈ کرو تاکہ تازہ ڈیٹا نظر آئے
        window.location.reload();
    } else {
        // ورنہ صرف کاؤنٹ اپ ڈیٹ کر دو
        updateCartCount();
    }
};
document.addEventListener("DOMContentLoaded", function () {
        updateCartCount();  // 
    }); 
function updateCartCount() {
    $.ajax({
        url: "/api_pharmacy/cart/count/?t=" + new Date().getTime(),
        type: "GET",
        cache: false,
        success: function (data) {
            // This updates any element with id="cart-count" (like your navbar badge)
            $("#cart-count").text(data.count || 0);
        },
        error: function () {
            $("#cart-count").text(0);
        }
    });
}

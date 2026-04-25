// cartcount.js
  document.addEventListener("DOMContentLoaded", function () {
        updateCartCount();  // 🔥 ہر page پر run ہوگا
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

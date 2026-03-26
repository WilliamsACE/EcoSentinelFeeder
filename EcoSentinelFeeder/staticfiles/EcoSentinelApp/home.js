const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add("visible"), i * 80);
      }
    });
  },
  { threshold: 0.1 },
);
document.querySelectorAll(".fade-in").forEach((el) => observer.observe(el));

document.querySelectorAll(".step").forEach((el, i) => {
  el.style.transitionDelay = `${i * 80}ms`;
});



let selectedAmount = 200;
let isCustom = false;

function selectAmount(btn, amount) {
  document
    .querySelectorAll(".amount-pill")
    .forEach((p) => p.classList.remove("active"));
  btn.classList.add("active");

  if (amount === "custom") {
    isCustom = true;
    selectedAmount = null;

  
    document.getElementById("customAmountInput")?.focus();
    

    updateDonateLink("custom", "otro monto");
    return;
  }

  isCustom = false;
  selectedAmount = amount;
  

  const customInput = document.getElementById("customAmountInput");
  if (customInput) {
    customInput.value = "";
  }

  updateDonateLink(amount, "$" + amount.toLocaleString());
}

function updateDonateLink(amount, textToShow) {
  const links = {
    custom: "https://buy.stripe.com/test_aFacN54srfj48q896w0Jq00",
    50: "https://buy.stripe.com/test_7sYdR9e313Am5dW96w0Jq01",
    100: "https://buy.stripe.com/test_4gMeVd2kj2wigWEfuU0Jq02",
    200: "https://buy.stripe.com/test_9B6bJ1gb9gn86i00A00Jq03",
    500: "https://buy.stripe.com/test_3cI9AT0cb8UG21K5Uk0Jq04"
  };


  const donateBtn = document.getElementById("donateBtn"); 
  if (!donateBtn) return;

  donateBtn.href = links[amount];
  

  donateBtn.innerHTML = `Donar <span id="donateAmount">${textToShow}</span> →`;
}
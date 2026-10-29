// DemoStays: an AI-built Airbnb-style demo. Fictional listings, no real bookings or payments.
const STAYS = [
  { id: 1, title: "Infinity-pool villa by the sea", place: "Malibu, California", cat: "Beach", price: 420, rating: 4.96, reviews: 128, host: "Maya", img: "img/villa.jpg", lat: 34.03, lng: -118.78, guests: 6, beds: 3,
    amen: ["Infinity pool", "Ocean view", "Wifi", "Kitchen", "Free parking", "Hot tub"] },
  { id: 2, title: "Snowy A-frame cabin", place: "Lake Tahoe, California", cat: "Cabins", price: 235, rating: 4.92, reviews: 211, host: "Ben", img: "img/cabin.jpg", lat: 39.1, lng: -120.03, guests: 4, beds: 2,
    amen: ["Fireplace", "Mountain view", "Wifi", "Kitchen", "Ski storage", "Heating"] },
  { id: 3, title: "Skyline loft with big windows", place: "Brooklyn, New York", cat: "City", price: 189, rating: 4.88, reviews: 342, host: "Ana", img: "img/loft.jpg", lat: 40.69, lng: -73.98, guests: 2, beds: 1,
    amen: ["City view", "Wifi", "Workspace", "Washer", "Elevator", "Coffee maker"] },
  { id: 4, title: "Rainforest treehouse", place: "Monteverde, Costa Rica", cat: "Treehouses", price: 310, rating: 4.98, reviews: 96, host: "Luis", img: "img/treehouse.jpg", lat: 10.3, lng: -84.82, guests: 2, beds: 1,
    amen: ["Forest view", "Breakfast", "Wifi", "Deck", "Bird watching", "Outdoor shower"] },
  { id: 5, title: "Stargazing desert dome", place: "Joshua Tree, California", cat: "Domes", price: 265, rating: 4.94, reviews: 174, host: "Kai", img: "img/dome.jpg", lat: 34.13, lng: -116.31, guests: 2, beds: 1,
    amen: ["Fire pit", "Telescope", "Air conditioning", "Kitchenette", "Free parking", "Hammock"] },
  { id: 6, title: "Lakeside cottage with dock", place: "Muskoka, Ontario", cat: "Lakes", price: 205, rating: 4.9, reviews: 158, host: "Emma", img: "img/lake.jpg", lat: 45.04, lng: -79.31, guests: 5, beds: 3,
    amen: ["Lake access", "Canoe", "Wifi", "Kitchen", "Fireplace", "BBQ grill"] },
];
const CATS = [["All", "🏠"], ["Beach", "🏖️"], ["Cabins", "🛖"], ["City", "🏙️"], ["Treehouses", "🌳"], ["Domes", "⛺"], ["Lakes", "🛶"]];
const REVIEWS = ["Even better than the photos. We didn't want to leave.", "Spotless, quiet and the host replied in minutes.", "Perfect for a long weekend. Would book again."];

const state = { cat: "All", where: "", guests: 2, checkIn: "", checkOut: "", liked: new Set(), map: false };
const $ = s => document.querySelector(s);
const money = n => "$" + n.toLocaleString("en-US");
const nightsOf = (a, b) => (a && b) ? Math.max(1, Math.round((new Date(b) - new Date(a)) / 86400000)) : 5;

function filtered() {
  return STAYS.filter(s => (state.cat === "All" || s.cat === state.cat)
    && (!state.where || (s.place + " " + s.title).toLowerCase().includes(state.where.toLowerCase()))
    && s.guests >= state.guests);
}

function home() {
  const list = filtered();
  const chips = `<nav class="chips">${CATS.map(([c, i]) => `<button class="chip ${state.cat === c ? "on" : ""}" data-cat="${c}"><span class="ic">${i}</span>${c}</button>`).join("")}</nav>`;
  if (state.map) {
    $("#app").innerHTML = chips + `<div id="map"></div><button class="mapbtn" id="toggleMap">Show list ☰</button>`;
    const map = L.map("map", { zoomControl: false }).setView([37, -100], 3);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap" }).addTo(map);
    list.forEach(s => L.marker([s.lat, s.lng], { icon: L.divIcon({ className: "", html: `<div class="pricepin">${money(s.price)}</div>` }) })
      .addTo(map).on("click", () => location.hash = "#/stay/" + s.id));
    if (list.length) map.fitBounds(list.map(s => [s.lat, s.lng]), { padding: [40, 40], maxZoom: 6 });
  } else {
    $("#app").innerHTML = chips + (list.length ? `<section class="grid">${list.map(card).join("")}</section>` : `<p class="empty">No stays match. Try another place or fewer guests.</p>`)
      + `<button class="mapbtn" id="toggleMap">Show map 🗺️</button>`;
  }
  document.querySelectorAll(".chip").forEach(b => b.onclick = () => { state.cat = b.dataset.cat; home(); });
  document.querySelectorAll(".heart").forEach(b => b.onclick = e => { e.preventDefault(); const id = +b.dataset.id;
    state.liked.has(id) ? state.liked.delete(id) : state.liked.add(id); b.classList.toggle("on"); });
  $("#toggleMap").onclick = () => { state.map = !state.map; home(); };
}

function card(s) {
  return `<a class="card" href="#/stay/${s.id}">
    <div class="ph"><img src="${s.img}" alt="${s.title}"><span class="tag">Guest favorite</span>
      <button class="heart ${state.liked.has(s.id) ? "on" : ""}" data-id="${s.id}" aria-label="Save">♥</button></div>
    <div class="meta"><span>${s.place}</span><span>★ ${s.rating.toFixed(2)}</span></div>
    <div class="sub">${s.title}</div>
    <div class="price"><b>${money(s.price)}</b> night</div></a>`;
}

function stay(id) {
  const s = STAYS.find(x => x.id === id); if (!s) return home();
  const n = nightsOf(state.checkIn, state.checkOut);
  $("#app").innerHTML = `<article class="detail">
    <img class="hero" src="${s.img}" alt="${s.title}">
    <div class="dwrap">
      <h1>${s.title}</h1>
      <div class="muted">${s.place} · ${s.guests} guests · ${s.beds} bedrooms</div>
      <div><b>★ ${s.rating.toFixed(2)}</b> · <u>${s.reviews} reviews</u></div>
      <hr class="hr">
      <div class="host"><div class="avatar">${s.host[0]}</div><div><b>Hosted by ${s.host}</b><div class="muted">Top host · replies within an hour</div></div></div>
      <hr class="hr">
      <h3>What this place offers</h3>
      <div class="amen">${s.amen.map(a => `<div>✓ ${a}</div>`).join("")}</div>
      <hr class="hr">
      <h3>★ ${s.rating.toFixed(2)} · ${s.reviews} reviews</h3>
      ${REVIEWS.map((r, i) => `<div class="rev"><b>${["Priya", "Tom", "Sofia"][i]}</b><div>${r}</div></div>`).join("")}
      <hr class="hr">
      <div class="boxed">
        <div class="row2"><label>Check-in<input type="date" id="dIn" value="${state.checkIn}"></label><label>Check-out<input type="date" id="dOut" value="${state.checkOut}"></label></div>
        <label>Guests<select id="dGuests">${[1, 2, 3, 4, 5, 6].filter(g => g <= s.guests).map(g => `<option ${g === Math.min(state.guests, s.guests) ? "selected" : ""}>${g}</option>`).join("")}</select></label>
        <div class="lines" id="lines"></div>
      </div>
    </div>
    <div class="book"><div class="row"><div><b>${money(s.price)}</b> night<div class="muted" id="bookSum"></div></div>
      <button class="primary" id="reserve">Reserve</button></div></div>
  </article>`;
  const upd = () => {
    state.checkIn = $("#dIn").value; state.checkOut = $("#dOut").value;
    const nn = nightsOf(state.checkIn, state.checkOut), base = s.price * nn, clean = 65, svc = Math.round(base * 0.12);
    $("#lines").innerHTML = `<div><span>${money(s.price)} x ${nn} nights</span><span>${money(base)}</span></div>
      <div><span>Cleaning fee</span><span>${money(clean)}</span></div><div><span>Service fee</span><span>${money(svc)}</span></div>
      <div class="tot"><span>Total</span><span>${money(base + clean + svc)}</span></div>`;
    $("#bookSum").textContent = `${nn} nights · ${money(base + clean + svc)} total`;
  };
  ["#dIn", "#dOut"].forEach(q => $(q).onchange = upd); upd();
  $("#reserve").onclick = () => location.hash = "#/checkout/" + s.id;
  window.scrollTo(0, 0);
}

function checkout(id) {
  const s = STAYS.find(x => x.id === id); if (!s) return home();
  const nn = nightsOf(state.checkIn, state.checkOut), base = s.price * nn, total = base + 65 + Math.round(base * 0.12);
  $("#app").innerHTML = `<div class="dwrap">
    <h1>Confirm and pay</h1>
    <div class="notice">Demo only: these fields are locked. No payment details are collected or charged.</div>
    <div class="boxed host"><img src="${s.img}" alt="" style="width:90px;height:70px;object-fit:cover;border-radius:10px">
      <div><b>${s.title}</b><div class="muted">${nn} nights · ${money(total)} total</div></div></div>
    <hr class="hr">
    <label>Card number<input id="card" value="4242 4242 4242 4242 (demo)" readonly disabled></label>
    <div class="row2"><label>Expiry<input value="12/28" readonly disabled></label><label>CVC<input value="123" readonly disabled></label></div>
    <label>Name on card<input value="Test Guest" readonly disabled></label>
    <button class="primary" id="pay" style="width:100%;margin-top:6px">Confirm and pay ${money(total)}</button>
  </div>`;
  $("#pay").onclick = () => { sessionStorage.setItem("lastTrip", JSON.stringify({ id: s.id, total, nn })); location.hash = "#/trips"; };
  window.scrollTo(0, 0);
}

function trips() {
  let t = null; try { t = JSON.parse(sessionStorage.getItem("lastTrip")); } catch (e) {}
  const s = t && STAYS.find(x => x.id === t.id);
  $("#app").innerHTML = s ? `<div class="done"><div class="big">🎉</div><h1>You're going to ${s.place.split(",")[0]}!</h1>
      <div class="muted">${s.title} · ${t.nn} nights · ${money(t.total)}</div>
      <div class="code">DEMO-${(1000 + s.id * 37) % 10000}</div>
      <p class="muted">Demo booking: nothing was charged.</p><a class="primary" href="#/" style="display:inline-block;margin-top:10px">Back to stays</a></div>`
    : `<p class="empty">No trips yet.</p>`;
}

function route() {
  const h = location.hash || "#/";
  const m = h.match(/^#\/(stay|checkout)\/(\d+)/);
  if (m) return m[1] === "stay" ? stay(+m[2]) : checkout(+m[2]);
  if (h.startsWith("#/trips")) return trips();
  home();
}

$("#openSearch").onclick = () => { $("#searchSheet").hidden = false; $("#qWhere").focus(); };
$("#closeSearch").onclick = () => { state.where = ""; $("#qWhere").value = ""; $("#searchSheet").hidden = true; $("#pillWhere").textContent = "Anywhere"; route(); };
$("#doSearch").onclick = () => {
  state.where = $("#qWhere").value.trim(); state.guests = +$("#qGuests").value;
  state.checkIn = $("#qIn").value; state.checkOut = $("#qOut").value;
  $("#pillWhere").textContent = state.where || "Anywhere";
  $("#pillDates").textContent = state.checkIn && state.checkOut ? `${nightsOf(state.checkIn, state.checkOut)} nights` : "Any week";
  $("#pillGuests").textContent = `${state.guests} guests`;
  $("#searchSheet").hidden = true; location.hash = "#/"; route();
};
window.addEventListener("hashchange", route);
route();

(() => {
  const tbody = document.getElementById("line-items-body");
  const addButton = document.getElementById("add-line-item-btn");
  if (!tbody || !addButton) {
    return;
  }

  const createRow = () => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><input name="item_description" placeholder="Item description"></td>
      <td><input name="item_quantity" type="number" min="0" step="0.01" value="1"></td>
      <td><input name="item_unit_price" type="number" min="0" step="0.01"></td>
      <td><button type="button" class="btn remove-line-item-btn">Remove</button></td>
    `;
    return row;
  };

  addButton.addEventListener("click", () => {
    tbody.appendChild(createRow());
  });

  tbody.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || !target.classList.contains("remove-line-item-btn")) {
      return;
    }
    if (tbody.rows.length <= 1) {
      return;
    }
    const row = target.closest("tr");
    if (row) {
      row.remove();
    }
  });
})();

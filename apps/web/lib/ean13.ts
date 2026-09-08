const leftOdd: Record<string, string> = {
  "0": "0001101", "1": "0011001", "2": "0010011", "3": "0111101", "4": "0100011",
  "5": "0110001", "6": "0101111", "7": "0111011", "8": "0110111", "9": "0001011",
};

const leftEven: Record<string, string> = {
  "0": "0100111", "1": "0110011", "2": "0011011", "3": "0100001", "4": "0011101",
  "5": "0111001", "6": "0000101", "7": "0010001", "8": "0001001", "9": "0010111",
};

const right: Record<string, string> = {
  "0": "1110010", "1": "1100110", "2": "1101100", "3": "1000010", "4": "1011100",
  "5": "1001110", "6": "1010000", "7": "1000100", "8": "1001000", "9": "1110100",
};

const parity: Record<string, string> = {
  "0": "LLLLLL", "1": "LLGLGG", "2": "LLGGLG", "3": "LLGGGL", "4": "LGLLGG",
  "5": "LGGLLG", "6": "LGGGLL", "7": "LGLGLG", "8": "LGLGGL", "9": "LGGLGL",
};

export function encodeEan13(value: string): string | null {
  if (!/^\d{13}$/.test(value)) return null;
  const digits = [...value];
  const leftParity = parity[digits[0]];
  const leftBits = digits.slice(1, 7).map((digit, index) => (
    leftParity[index] === "L" ? leftOdd[digit] : leftEven[digit]
  )).join("");
  const rightBits = digits.slice(7).map((digit) => right[digit]).join("");
  return `101${leftBits}01010${rightBits}101`;
}

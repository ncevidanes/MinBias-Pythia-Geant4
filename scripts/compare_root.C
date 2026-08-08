#include <TBranch.h>
#include <TFile.h>
#include <TLeaf.h>
#include <TLeafC.h>
#include <TObjArray.h>
#include <TTree.h>

#include <cmath>
#include <cstring>
#include <iostream>
#include <string>

namespace {

bool SameDoubleBits(const double left, const double right) {
  return std::memcmp(&left, &right, sizeof(double)) == 0;
}

TLeaf* FindOnlyLeaf(TBranch& branch) {
  if (auto* leaf = branch.GetLeaf(branch.GetName())) {
    return leaf;
  }
  TObjArray* leaves = branch.GetListOfLeaves();
  if (leaves && leaves->GetEntries() == 1) {
    return static_cast<TLeaf*>(leaves->At(0));
  }
  return nullptr;
}

bool CompareTree(TTree& left, TTree& right, int& differences) {
  const std::string treeName = left.GetName();
  if (left.GetEntries() != right.GetEntries()) {
    std::cerr << "[DIFF] " << treeName << ": número de entradas\n";
    ++differences;
    return false;
  }

  TObjArray* leftBranches = left.GetListOfBranches();
  TObjArray* rightBranches = right.GetListOfBranches();
  if (leftBranches->GetEntries() != rightBranches->GetEntries()) {
    std::cerr << "[DIFF] " << treeName << ": número de branches\n";
    ++differences;
    return false;
  }

  for (int index = 0; index < leftBranches->GetEntries(); ++index) {
    auto* leftBranch = static_cast<TBranch*>(leftBranches->At(index));
    auto* rightBranch = right.GetBranch(leftBranch->GetName());
    if (!rightBranch) {
      std::cerr << "[DIFF] " << treeName << ": branch ausente: "
                << leftBranch->GetName() << '\n';
      ++differences;
      return false;
    }
  }

  for (Long64_t entry = 0; entry < left.GetEntries(); ++entry) {
    left.GetEntry(entry);
    right.GetEntry(entry);

    for (int index = 0; index < leftBranches->GetEntries(); ++index) {
      auto* leftBranch = static_cast<TBranch*>(leftBranches->At(index));
      auto* rightBranch = right.GetBranch(leftBranch->GetName());
      TLeaf* leftLeaf = FindOnlyLeaf(*leftBranch);
      TLeaf* rightLeaf = FindOnlyLeaf(*rightBranch);
      if (!leftLeaf || !rightLeaf ||
          std::string(leftLeaf->GetTypeName()) != rightLeaf->GetTypeName() ||
          leftLeaf->GetLen() != rightLeaf->GetLen()) {
        std::cerr << "[DIFF] " << treeName << '.' << leftBranch->GetName()
                  << ": tipo ou dimensão\n";
        ++differences;
        return false;
      }

      auto* leftText = dynamic_cast<TLeafC*>(leftLeaf);
      auto* rightText = dynamic_cast<TLeafC*>(rightLeaf);
      if ((leftText == nullptr) != (rightText == nullptr)) {
        std::cerr << "[DIFF] " << treeName << '.' << leftBranch->GetName()
                  << ": representação textual\n";
        ++differences;
        return false;
      }
      if (leftText) {
        const auto* leftValue =
            static_cast<const char*>(leftText->GetValuePointer());
        const auto* rightValue =
            static_cast<const char*>(rightText->GetValuePointer());
        if (!leftValue || !rightValue ||
            std::strcmp(leftValue, rightValue) != 0) {
          std::cerr << "[DIFF] " << treeName << '.'
                    << leftBranch->GetName() << " na entrada " << entry
                    << '\n';
          ++differences;
          return false;
        }
        continue;
      }

      for (int element = 0; element < leftLeaf->GetLen(); ++element) {
        if (!SameDoubleBits(leftLeaf->GetValue(element),
                            rightLeaf->GetValue(element))) {
          std::cerr << "[DIFF] " << treeName << '.' << leftBranch->GetName()
                    << " na entrada " << entry << '\n';
          ++differences;
          return false;
        }
      }
    }
  }

  left.ResetBranchAddresses();
  right.ResetBranchAddresses();
  return true;
}

}  // namespace

void compare_root(const char* leftFilename, const char* rightFilename) {
  TFile leftFile(leftFilename, "READ");
  TFile rightFile(rightFilename, "READ");
  int differences = 0;

  if (leftFile.IsZombie() || rightFile.IsZombie()) {
    std::cerr << "[DIFF] não foi possível abrir os dois arquivos\n";
    std::cout << "COMPARE_RESULT=FAIL differences=1\n";
    return;
  }

  for (const char* name : {"events", "hits", "generator", "metadata"}) {
    auto* leftTree = leftFile.Get<TTree>(name);
    auto* rightTree = rightFile.Get<TTree>(name);
    if (!leftTree || !rightTree) {
      std::cerr << "[DIFF] TTree ausente: " << name << '\n';
      ++differences;
      continue;
    }
    CompareTree(*leftTree, *rightTree, differences);
  }

  if (differences == 0) {
    std::cout << "COMPARE_RESULT=PASS\n";
  } else {
    std::cout << "COMPARE_RESULT=FAIL differences=" << differences << '\n';
  }
}

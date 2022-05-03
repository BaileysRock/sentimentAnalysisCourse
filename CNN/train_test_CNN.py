import time
import torch
import torch.nn.functional as F
from tensorboardX import SummaryWriter
from sklearn import metrics
import numpy as np
from tqdm import tqdm
def train(config,model,train_iter,dev_iter):
    start_time = time.time()
    # 启用dropout
    model.train()
    # 设置adam优化器
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)

    total_batch = 0                # 记录总共训练的批次
    dev_best_loss = float('inf')   # 记录验证集上最低的loss
    dev_best_acc = float(0)        # 记录验证集上最高的acc
    dev_best_f1score = float(0)    # 记录验证集上最高的f1score
    last_improve = 0               # 记录上一次dev的loss下降时的批次
    flag = False                   # 是否结束训练
    writer = SummaryWriter(log_dir=config.log_path + time.strftime('%m-%d_%H.%M', time.localtime()))
    for epoch in range(config.epoch):
        print("Epoch [{}/{}]".format(epoch+1, config.epoch))
        for i,(trains,labels) in enumerate(train_iter):
            outputs = model(trains)
            model.zero_grad()
            loss = F.cross_entropy(outputs, labels)
            loss.backward()
            optimizer.step()
            # 输出当前效果
            if total_batch % 10 == 0:
                ground_truth = labels.data.cpu()
                predict_labels = torch.max(outputs.data,1)[1].cpu()
                train_acc = metrics.accuracy_score(ground_truth, predict_labels)
                dev_acc, dev_loss, dev_f1score = evaluate(model, dev_iter)
                if dev_loss < dev_best_loss:
                    dev_best_loss = dev_loss
                    torch.save(model.state_dict(), config.save_model_path)
                    improve = '*'
                    last_improve = total_batch
                else:
                    improve = ''
                if dev_acc > dev_best_acc:
                    dev_best_acc = dev_acc
                if dev_f1score > dev_best_f1score:
                    dev_best_f1score = dev_f1score
                print("Iter:{:4d} TrainLoss:{:.12f} TrainAcc:{:.5f} DevLoss:{:.12f} DevAcc:{:.5f} DevF1Score:{:.2f} Improve:{}".format(total_batch, loss.item(), train_acc, dev_loss, dev_acc, dev_f1score, improve))
                writer.add_scalar("loss/train", loss.item(), total_batch)
                writer.add_scalar("loss/dev", dev_loss, total_batch)
                writer.add_scalar("acc/train", train_acc, total_batch)
                writer.add_scalar("acc/dev", dev_acc, total_batch)
                model.train()
            total_batch += 1
            if total_batch - last_improve > config.maxiter_without_improvement:
                print("No optimization for a long time, auto-stopping...")
                flag = True
                break
        if flag:
            break
    writer.close()
    end_time = time.time()
    print("Train Time : {:.3f} min , The Best Acc in Dev : {} % , The Best f1-score in Dev : {}".format(((float)((end_time-start_time))/60), dev_best_acc,dev_best_f1score))


def evaluate(model, dev_iter):
    model.eval()
    loss_total = 0
    predict_all = np.array([], dtype=int)
    labels_all = np.array([], dtype=int)
    with torch.no_grad():
        for texts, labels in dev_iter:
            outputs = model(texts)
            loss = F.cross_entropy(outputs, labels)
            loss_total += loss
            ground_truth = labels.cpu().data.numpy()
            predict_labels = torch.max(outputs.cpu().data, 1)[1].numpy()
            labels_all = np.append(labels_all, ground_truth)
            predict_all = np.append(predict_all, predict_labels)
    acc = metrics.accuracy_score(labels_all, predict_all)
    f1score = metrics.f1_score(labels_all, predict_all, average='macro')
    return acc, loss_total / len(dev_iter), f1score



def test(config,model,test_iter):
    start_time = time.time()
    model.eval()
    predict_all = np.array([], dtype=int)
    with torch.no_grad():
        for i, (trains) in tqdm(enumerate(test_iter)):
            outputs = model(trains)
            predict_all = np.append(predict_all, torch.max(outputs.cpu().data, 1)[1].numpy())
    end_time = time.time()
    print("Predict Time : {} s".format(((float)(end_time-start_time))))
    predict_result = np.column_stack([test_iter.ids, predict_all])
    np.savetxt(config.predict_save, predict_result.astype(int), delimiter=',', fmt='%d,%d',encoding='utf-8')




















# python flow.py run

import time
from metaflow import step, FlowSpec, resources, kubernetes, catch, trigger, pypi_base, card
from metaflow.cards import Markdown, Table, Image

# Branch parallelism

sleep_time = 5

class BranchFlow(FlowSpec):
    @step
    def start(self):
        # my_param = Parameter("my_param", default=1) # will be set from outside and is read-only: python flow.py run --my_param 10

	    # initialize the artifact x which will persist through the pipeline
        self.x = 1 
        print("Starting 👋")
        self.next(self.eat, self.drink)

    # eat and drink will be 2 parallel steps in the pipeline which we will join together
    @step
    def eat(self):
        print("Pausing to eat... 🍜")
        self.x += 1
        time.sleep(sleep_time)
        self.next(self.join)

    @step
    def drink(self):
        print("Pausing to drink... 🥤")
        time.sleep(sleep_time)
        self.next(self.join)

    @step
    def join(self, inputs):
        print("Joining 🖇️")
        self.x = sum(i.x for i in inputs) # aggregate result after merging
        self.next(self.end)

    @step
    def end(self):
        print("the value of x is", self.x) # x is 3 now
        print("Done! 🏁")

# Foreach parallelism

# @trigger(event={"name": "my_event"}) # uncomment for triggering pipeline after event
# @pypi_base(
#     packages={
#         "scikit-learn": "1.5.2",
#         "pandas": "2.2.2",
#         "pyarrow": "17.0.0",
#         "matplotlib": "3.9.2",
#     }
# )
# Do imports in the steps themselves!

class ForeachFlow(FlowSpec):
    # @card(type="blank") # for human-readable report
    @step
    def start(self):
        #self.plot = plot(self.y_test, self.y_pred)
        #current.card.append(Markdown("# Model Report"))
        #current.card.append(
        #    Table(
        #        [
        #            ["Random Forest", float(self.model_rmse)],
        #            ["Baseline", float(self.baseline_rmse)],
        #        ],
        #        headers=["Model", "RMSE"],
        #    )
        #)
        #current.card.append(Image(self.plot, label="Correct vs. Predicted Fare"))

        self.data = ["Apple", "Orange", "Watermelon"]
        self.next(self.process, foreach="data")

    #def plot(correct, predicted):
    #    import matplotlib.pyplot as plt
    #    from io import BytesIO
    #    import numpy
    #
    #    MAX_FARE = 100
    #    line = numpy.arange(0, MAX_FARE, MAX_FARE / 1000)
    #    plt.rcParams.update({"font.size": 22})
    #    plt.scatter(x=correct, y=predicted, alpha=0.01, linewidth=0.5)
    #    plt.plot(line, line, linewidth=2, color="black")
    #    plt.xlabel("Correct fare")
    #    plt.ylabel("Predicted fare")
    #    plt.xlim([0, MAX_FARE])
    #    plt.ylim([0, MAX_FARE])
    #    fig = plt.gcf()
    #    fig.set_size_inches(18, 10)
    #    buf = BytesIO()
    #    fig.savefig(buf) # or for other types of images: img.to_pil().save(buf, format="png")
    #    return buf.getvalue()

    # @kubernetes # uncomment for cloud
    @step
    def process(self):
        print("Processing:", self.input)
        self.fruit = self.input
        self.score = len(self.input)
        self.next(self.memory_hog)

    # @kubernetes(memory=10000) # uncomment for cloud
    @catch # handle error and continue
    # @retry # retry when error
    # @timeout # step can only run a limited time
    @step
    def memory_hog(self):
        print("Requesting a lot of memory")
        self.bytes_used = len("x" * 1_000_000_000)
        print("Success!")
        self.next(self.join)

    @step
    def join(self, inputs):
        print("Choosing the best fruit")
        self.best = max(inputs, key=lambda x: x.score).fruit
        print("Best fruit:", self.best)
        self.next(self.end)

    @step
    def end(self):
        pass


if __name__ == "__main__":
    BranchFlow()
    # ForeachFlow()

# Publish this event to evoke the subscribing pipeline ForeachFlow
"""
from metaflow.integrations import ArgoEvent
ArgoEvent(name="my_event").publish(payload={"greeting": "Kitty!"})
"""